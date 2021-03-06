# Python imports
import sys
import os.path
from django.utils import unittest
import simplejson as json
from datetime import date
                
crt = os.path.dirname(os.path.realpath(__file__))
DJANGO_PATH = crt[:crt.rfind('/')]
if DJANGO_PATH not in sys.path:
    sys.path.append(DJANGO_PATH)
from django.core.management import setup_environ
import settings
setup_environ(settings)

# Django imports
from nystatus.models import *
from nystatus.templatetags.pversion import pversion

# My imports
from client import Client
from ChangelogClient import ChangelogClient


def sampledata(filename):
    f = open(os.path.join(settings.ABS_ROOT,
                          'nystatus' + os.path.sep + 'testdata' + os.path.sep +
                          filename),
             'r')
    content = f.read()
    f.close()
    return content


class ClientTestCase(unittest.TestCase):
    instance = 'xxxTesting Instancexxx'
    url = 'http://testing.test'
    json_getProducts = ('[{"version": "0.0.0-1", "name": "Fictional prod 0"}, {"version":'
    '"1.0.1-2", "name": "Fictional prod 1"}, {"version": "2.0.2-3", "name":'
    '"Fictional prod 2"}, {"version": "3.0.3-4", "name": "Fictional prod 3"}]')
    json_getPortals = ('["fake_portal0", "fake_portal1", "fake_portal2", '
                        '"fake_portal3"]')
    json_getErrors = sampledata('json_errors.json')

    pcount = 4
    ins = None
    cl = Client()

    def setUp(self):
        # will throw exception for first test case
        try:
            self.ins = ZopeInstance.objects.get(instance_name=self.instance)
        except Exception:
            self.ins = ZopeInstance(instance_name=self.instance, url=self.url)
            self.ins.save()
        self.cl.update_products(self.ins, json.loads(self.json_getProducts))

    def tearDown(self):
        Portal.objects.filter(parent_instance__instance_name__exact=self.instance).delete()        
        OnlineProduct.objects.filter(zopeinstance__instance_name__exact=self.instance).delete()
        Product.objects.filter(name__startswith="Fictional prod ").delete()
        ZopeInstance.objects.filter(instance_name__exact=self.instance).delete()


    def test_0added_instance(self):
        ins = ZopeInstance.objects.get(instance_name=self.instance)
        ins = ZopeInstance.objects.get(pk=ins.pk)
        self.assertEqual(ins.up_to_date, True)
        self.assertEqual(ins.status, 'OK')
        self.assertEqual(ins.no_products, self.pcount)

    def test_1added_products(self):
        products = self.ins.products.all()
        self.assertEqual(len(products), self.pcount)
        self.assertEqual(products[0].use_count, 1)

    def test_2changed_products(self):
        # Simulate we now have only one product
        # newer than the one existent
        only_one = '[{"version": "0.0.0-2", "name": "Fictional prod 0"}]'
        self.cl.update_products(self.ins, json.loads(only_one))
        ins = ZopeInstance.objects.get(pk=self.ins.pk)
        self.assertEqual(self.ins.no_products, 1)
        prods = Product.objects.filter(name__startswith="Fictional prod") \
                               .order_by('name')
        # prod count must be unchanged - functional prod existed
        self.assertEqual(len(prods), self.pcount)
        self.assertEqual(prods[0].latest_found_version, "0.0.0-2")
        self.assertEqual(prods[0].use_count, 1)
        self.assertEqual(prods[1].use_count, 0)

    def test_3failed_grab(self):
        (p, success) = self.cl.grab_json(self.ins)
        self.assertFalse(success)
        self.ins = ZopeInstance.objects.get(pk=self.ins.pk)
        self.assertEqual(self.ins.status.find("Can not connect"), 0)

    def test_4portals(self):
        self.cl.update_portals(self.ins, self.json_getPortals)
        portals = Portal.objects.filter(parent_instance=self.ins)
        self.assertEqual(len(portals), self.pcount)
        self.cl.update_errors(self.ins, portals[0], self.json_getErrors)
        errors = Error.objects.filter(portal__parent_instance=self.ins)
        self.assertEqual(len(errors), self.pcount)
        self.cl.update_errors(self.ins, portals[0], self.json_getErrors)
        self.assertEqual(len(errors), self.pcount)

    def assertVersion(self,v,v_latest):
        self.assertEqual(self.cl.later_version(v[0], v[1]), v_latest)

    def test_compare_versions(self):
        self.assertVersion(("0.0.0.1", "0.0.0.0.1"), "0.0.0.1")
        self.assertVersion(("0.0.1", "0.1"), "0.1")
        self.assertVersion(("0", "0.1"), "0.1")
        self.assertVersion(("1-b", "1"), "1-b")
        self.assertVersion(("22.34", "22.33"), "22.34")
        self.assertVersion(("22.34", "22"), "22.34")
        self.assertVersion(("22", "22.33"), "22.33")


class ChangelogClientTestCase(unittest.TestCase):

    sample = {'changelog0': sampledata('changelog0.txt'),
              'changelog1': sampledata('changelog1.txt'),
              'name': 'naaya-survey'}

    def setUp(self):
        self.product = Product(name=self.sample['name'], origin='n')
        self.product.save()
        self.client = ChangelogClient(self.product)

    def test_changelog_parser(self):
        self.client.update_changelog(self.sample['changelog0'])
        versions = Release.objects.filter(product=self.product)
        indexed = {}
        for v in versions:
            indexed[pversion(v.version)] = v
        self.assertEqual(len(versions), 3)
        self.assertEqual(set(indexed.keys()), set(['1.2.2', '1.2.5', '1.2.6']))
        self.assertEqual(indexed['1.2.6'].datev, None)
        self.assertEqual(indexed['1.2.5'].datev, date(2011, 9, 23))
        self.assertEqual(indexed['1.2.2'].changelog, """* Last version where Products.NaayaSurvey and Products.NaayaWidgets were separate packages""")

    def test_changelog_incremental_update(self):
        self.client.update_changelog(self.sample['changelog0'])
        # this throws DoesNotExist / MultipleValues exception unless 1 result
        unreleased = Release.objects.get(product=self.product, datev=None)
        unreleased.obs = 'My personal observations aka extended changelog'
        unreleased.save()

        self.client.update_changelog(self.sample['changelog1'])
        versions = Release.objects.filter(product=self.product)
        indexed = {}
        for v in versions:
            indexed[pversion(v.version)] = v
        self.assertEqual(set(indexed.keys()),
                         set(['1.2.2', '1.2.5', '1.3.0', '1.3.1', '1.3.2']))
        self.assertEqual(indexed['1.3.0'].obs,
                         'My personal observations aka extended changelog')
        self.assertEqual(indexed['1.3.0'].datev, date(2011, 9, 30))
        self.assertEqual(indexed['1.3.0'].changelog,
                         """* Another bugfix that now looks ok
* bugfix: Bugfix in RadioWidget.get_value
* feature: Administrators can now edit answers in expired surveys""")
        self.assertEqual(indexed['1.3.2'].datev, None)
