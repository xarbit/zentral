from functools import reduce
import operator
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.urls import reverse
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import APIToken, User
from zentral.contrib.inventory.models import (CurrentMachineSnapshot, MachineSnapshot,
                                              MachineSnapshotCommit, MetaBusinessUnit, Tag, Taxonomy)


class InventoryAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            get_random_string(12),
            "{}@zentral.io".format(get_random_string(12)),
            get_random_string(12)
        )
        cls.group = Group.objects.create(name=get_random_string(12))
        cls.user.groups.set([cls.group])
        cls.api_key = APIToken.objects.update_or_create_for_user(user=cls.user)

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.api_key)

    # utils

    def _set_permissions(self, *permissions):
        if permissions:
            permission_filter = reduce(operator.or_, (
                Q(content_type__app_label=app_label, codename=codename)
                for app_label, codename in (
                    permission.split(".")
                    for permission in permissions
                )
            ))
            self.group.permissions.set(list(Permission.objects.filter(permission_filter)))
        else:
            self.group.permissions.clear()

    def commit_machine_snapshot(self, serial_number=None):
        if serial_number is None:
            serial_number = get_random_string(12)
        source = {"module": "tests.zentral.io", "name": "Zentral Tests"}
        tree = {
            "source": source,
            "business_unit": {"name": "yo bu",
                              "reference": "bu1",
                              "source": source,
                              "links": [{"anchor_text": "bu link",
                                         "url": "http://bu-link.de"}]},
            "groups": [{"name": "yo grp",
                        "reference": "grp1",
                        "source": source,
                        "links": [{"anchor_text": "group link",
                                   "url": "http://group-link.de"}]}],
            "serial_number": serial_number,
            "os_version": {'name': 'OS X', 'major': 10, 'minor': 11, 'patch': 1},
            "osx_app_instances": [
                {'app': {'bundle_id': 'io.zentral.baller',
                         'bundle_name': 'Baller.app',
                         'bundle_version': '123',
                         'bundle_version_str': '1.2.3'},
                 'bundle_path': "/Applications/Baller.app"}
            ]
        }
        MachineSnapshotCommit.objects.commit_machine_snapshot_tree(tree)
        return serial_number

    # archive machines

    def test_archive_machines_unauthorized(self):
        response = self.client.post(reverse('inventory_api:archive_machines'))
        self.assertEqual(response.status_code, 403)

    def test_archive_machines_wrong_permissions(self):
        self._set_permissions("inventory.view_machinesnapshot")
        response = self.client.post(reverse('inventory_api:archive_machines'))
        self.assertEqual(response.status_code, 403)

    def test_archive_machines_bad_request(self):
        self._set_permissions("inventory.change_machinesnapshot")
        response = self.client.post(reverse('inventory_api:archive_machines'),
                                    {"yolo": "fomo"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_archive_machines(self):
        serial_number = self.commit_machine_snapshot()
        serial_number2 = self.commit_machine_snapshot()
        self._set_permissions("inventory.change_machinesnapshot")
        response = self.client.post(reverse('inventory_api:archive_machines'),
                                    {"serial_numbers": [serial_number]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data,
                         {"current_machine_snapshots": 1})
        self.assertEqual(
            CurrentMachineSnapshot.objects.filter(serial_number__in=[serial_number, serial_number2]).count(),
            1
        )

    # prune machines

    def test_prune_machines_unauthorized(self):
        response = self.client.post(reverse('inventory_api:prune_machines'))
        self.assertEqual(response.status_code, 403)

    def test_prune_machines_wrong_permissions(self):
        self._set_permissions("inventory.change_machinesnapshot")
        response = self.client.post(reverse('inventory_api:prune_machines'))
        self.assertEqual(response.status_code, 403)

    def test_prune_machines_bad_request(self):
        self._set_permissions("inventory.delete_machinesnapshot")
        response = self.client.post(reverse('inventory_api:prune_machines'),
                                    {"yolo": "fomo"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_prune_machines(self):
        serial_number = self.commit_machine_snapshot()
        self.commit_machine_snapshot(serial_number)
        serial_number2 = self.commit_machine_snapshot()
        self._set_permissions("inventory.delete_machinesnapshot")
        response = self.client.post(reverse('inventory_api:prune_machines'),
                                    {"serial_numbers": [serial_number]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data,
                         {"current_machine_snapshots": 1,
                          "machine_snapshot_commits": 2,
                          "machine_snapshots": 1})
        self.assertEqual(
            CurrentMachineSnapshot.objects.filter(serial_number__in=[serial_number, serial_number2]).count(),
            1
        )
        self.assertEqual(
            MachineSnapshot.objects.filter(serial_number__in=[serial_number, serial_number2]).count(),
            1
        )
        self.assertEqual(
            MachineSnapshotCommit.objects.filter(serial_number__in=[serial_number, serial_number2]).count(),
            1
        )

    # machines export

    def test_export_machines_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machines_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machines(self):
        self._set_permissions("inventory.view_machinesnapshot")
        response = self.client.post(reverse('inventory_api:machines_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # Android apps export

    def test_export_android_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:android_apps_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_android_apps(self):
        self._set_permissions("inventory.view_androidapp")
        response = self.client.post(reverse('inventory_api:android_apps_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # Debian packages export

    def test_export_deb_packages_unauthorized(self):
        response = self.client.post(reverse('inventory_api:deb_packages_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_deb_packages(self):
        self._set_permissions("inventory.view_debpackage")
        response = self.client.post(reverse('inventory_api:deb_packages_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # iOS apps export

    def test_export_ios_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:ios_apps_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_ios_apps(self):
        self._set_permissions("inventory.view_iosapp")
        response = self.client.post(reverse('inventory_api:ios_apps_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # macOS apps export

    def test_export_macos_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:macos_apps_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_macos_apps(self):
        self._set_permissions("inventory.view_osxapp", "inventory.view_osxappinstance")
        response = self.client.post(reverse('inventory_api:macos_apps_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # Programs export

    def test_export_programs_unauthorized(self):
        response = self.client.post(reverse('inventory_api:programs_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_programs(self):
        self._set_permissions("inventory.view_program", "inventory.view_programinstance")
        response = self.client.post(reverse('inventory_api:programs_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine android apps export

    def test_export_machine_android_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_android_apps_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_android_apps(self):
        self._set_permissions("inventory.view_androidapp")
        response = self.client.post(reverse('inventory_api:machine_android_apps_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine Debian packages export

    def test_export_machine_deb_packages_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_deb_packages_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_deb_packages(self):
        self._set_permissions("inventory.view_debpackage")
        response = self.client.post(reverse('inventory_api:machine_deb_packages_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine iOS apps export

    def test_export_machine_ios_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_ios_apps_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_ios_apps(self):
        self._set_permissions("inventory.view_iosapp")
        response = self.client.post(reverse('inventory_api:machine_ios_apps_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine macos apps export

    def test_export_machine_macos_apps_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_macos_app_instances_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_macos_apps(self):
        self._set_permissions("inventory.view_osxapp", "inventory.view_osxappinstance")
        response = self.client.post(reverse('inventory_api:machine_macos_app_instances_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine program instances export

    def test_export_machine_program_instances_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_program_instances_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_program_instances(self):
        self._set_permissions("inventory.view_program", "inventory.view_programinstance")
        response = self.client.post(reverse('inventory_api:machine_program_instances_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # machine snapshots export

    def test_export_machine_snapshots_unauthorized(self):
        response = self.client.post(reverse('inventory_api:machine_snapshots_export'))
        self.assertEqual(response.status_code, 403)

    def test_export_machine_snapshots(self):
        self._set_permissions("inventory.view_machinesnapshot")
        response = self.client.post(reverse('inventory_api:machine_snapshots_export'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # cleanup

    def test_cleanup_unauthorized(self):
        response = self.client.post(reverse('inventory_api:cleanup'))
        self.assertEqual(response.status_code, 403)

    def test_cleanup_bad_request(self):
        self._set_permissions("inventory.delete_machinesnapshot")
        response = self.client.post(reverse('inventory_api:cleanup'), {"days": 7000})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"days": ["Ensure this value is less than or equal to 3660."]})

    def test_cleanup(self):
        self._set_permissions("inventory.delete_machinesnapshot")
        response = self.client.post(reverse('inventory_api:cleanup'), {"days": 70})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("task_id", response.data)
        self.assertIn("task_result_url", response.data)

    # create meta business unit

    def test_create_meta_business_unit_unauthorized(self):
        data = {'name': 'TestMBU0'}
        response = self.client.post(reverse('inventory_api:meta_business_units'), data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_create_meta_business_unit(self):
        data = {'name': 'TestMBU0'}
        self._set_permissions("inventory.add_metabusinessunit")
        response = self.client.post(reverse('inventory_api:meta_business_units'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MetaBusinessUnit.objects.filter(name='TestMBU0').count(), 1)
        meta_business_unit = MetaBusinessUnit.objects.get(name='TestMBU0')
        self.assertEqual(meta_business_unit.name, 'TestMBU0')
        self.assertFalse(meta_business_unit.api_enrollment_enabled())

    def test_create_api_enabled_meta_business_unit(self):
        url = reverse('inventory_api:meta_business_units')
        data = {'name': 'TestMBU1', 'api_enrollment_enabled': True}
        self._set_permissions("inventory.add_metabusinessunit")
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MetaBusinessUnit.objects.filter(name='TestMBU1').count(), 1)
        meta_business_unit = MetaBusinessUnit.objects.get(name='TestMBU1')
        self.assertEqual(meta_business_unit.name, 'TestMBU1')
        self.assertTrue(meta_business_unit.api_enrollment_enabled())

    def test_create_meta_business_unit_name_error(self):
        name = get_random_string(12)
        MetaBusinessUnit.objects.create(name=name)
        data = {'name': name}
        self._set_permissions("inventory.add_metabusinessunit")
        response = self.client.post(reverse('inventory_api:meta_business_units'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"name": ["meta business unit with this name already exists."]})

    # get meta business unit

    def test_get_meta_business_unit_unauthorized(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        response = self.client.get(reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_get_meta_business_unit(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        self._set_permissions("inventory.view_metabusinessunit")
        response = self.client.get(reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data,
                         {'id': meta_business_unit.pk,
                          'name': meta_business_unit.name,
                          'api_enrollment_enabled': meta_business_unit.api_enrollment_enabled(),
                          'created_at': meta_business_unit.created_at.isoformat(),
                          'updated_at': meta_business_unit.updated_at.isoformat()})

    # update meta business unit

    def test_update_meta_business_unit_unauthorized(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        response = self.client.put(reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_update_meta_business_unit(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        self.assertFalse(meta_business_unit.api_enrollment_enabled())
        self._set_permissions("inventory.change_metabusinessunit")
        url = reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,))
        updated_name = get_random_string(12)
        data = {'name': updated_name, 'api_enrollment_enabled': True}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meta_business_unit.refresh_from_db()
        self.assertEqual(meta_business_unit.name, updated_name)
        self.assertTrue(meta_business_unit.api_enrollment_enabled())

    def test_update_meta_business_unit_disable_api_enrollment_error(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        meta_business_unit.create_enrollment_business_unit()
        self.assertTrue(meta_business_unit.api_enrollment_enabled())
        self._set_permissions("inventory.change_metabusinessunit")
        url = reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,))
        data = {"name": get_random_string(12), 'api_enrollment_enabled': False}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data,
                         {"api_enrollment_enabled": [
                              "Cannot disable API enrollment"
                          ]})

    def test_update_meta_business_unit_name_error(self):
        name = get_random_string(12)
        MetaBusinessUnit.objects.create(name=name)
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        self._set_permissions("inventory.change_metabusinessunit")
        url = reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,))
        data = {'name': name, 'api_enrollment_enabled': False}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"name": ["meta business unit with this name already exists."]})

    # delete meta business unit

    def test_delete_meta_business_unit_unauthorized(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        url = reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,))
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_meta_business_unit(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        self._set_permissions("inventory.delete_metabusinessunit")
        url = reverse('inventory_api:meta_business_unit', args=(meta_business_unit.pk,))
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(MetaBusinessUnit.objects.filter(pk=meta_business_unit.pk).count(), 0)

    # list meta business unit

    def test_list_meta_business_unit_unauthorized(self):
        response = self.client.get(reverse('inventory_api:meta_business_units'))
        self.assertEqual(response.status_code, 403)

    def test_list_meta_business_unit(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        url = reverse('inventory_api:meta_business_units')
        self._set_permissions("inventory.view_metabusinessunit")
        response = self.client.get(url, {"name": meta_business_unit.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data,
                         [{"id": meta_business_unit.pk,
                           "name": meta_business_unit.name,
                           "api_enrollment_enabled": meta_business_unit.api_enrollment_enabled(),
                           "created_at": meta_business_unit.created_at.isoformat(),
                           "updated_at": meta_business_unit.updated_at.isoformat()}])

    # create tag

    def test_create_tag_unauthorized(self):
        data = {'name': 'TestTag0'}
        response = self.client.post(reverse('inventory_api:tags'), data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_create_tag(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        data = {'meta_business_unit': meta_business_unit.pk, 'name': 'TestTag0', 'color': 'ff0000'}
        self._set_permissions("inventory.add_tag")
        response = self.client.post(reverse('inventory_api:tags'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tag = Tag.objects.get(name='TestTag0')
        self.assertEqual(tag.meta_business_unit, meta_business_unit)
        self.assertEqual(tag.name, data["name"])
        self.assertEqual(tag.color, data["color"])
        self.assertEqual(
            response.data,
            {"id": tag.pk,
             "taxonomy": None,
             "meta_business_unit": meta_business_unit.pk,
             "name": tag.name,
             "slug": tag.slug,
             "color": tag.color}
        )

    # get tag

    def test_get_tag_unauthorized(self):
        tag = Tag.objects.create(name=get_random_string(12))
        response = self.client.get(reverse('inventory_api:tag', args=(tag.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_get_tag(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        tag = Tag.objects.create(meta_business_unit=meta_business_unit, name=get_random_string())
        self._set_permissions("inventory.view_tag")
        response = self.client.get(reverse('inventory_api:tag', args=(tag.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"id": tag.pk,
             "taxonomy": None,
             "meta_business_unit": meta_business_unit.pk,
             "name": tag.name,
             "slug": tag.slug,
             "color": tag.color}
        )

    # update tag

    def test_update_tag_unauthorized(self):
        tag = Tag.objects.create(name=get_random_string(12))
        response = self.client.put(reverse('inventory_api:tag', args=(tag.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_update_tag(self):
        tag = Tag.objects.create(name=get_random_string(12))
        self._set_permissions("inventory.change_tag")
        url = reverse('inventory_api:tag', args=(tag.pk,))
        updated_name = get_random_string(12)
        data = {'name': updated_name}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, updated_name)

    def test_update_tag_name_error(self):
        name = get_random_string(12)
        Tag.objects.create(name=name)
        tag = Tag.objects.create(name=get_random_string())
        self._set_permissions("inventory.change_tag")
        url = reverse('inventory_api:tag', args=(tag.pk,))
        data = {'name': name}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"name": ["tag with this name already exists."]})

    # delete tag

    def test_delete_tag_unauthorized(self):
        tag = Tag.objects.create(name=get_random_string(12))
        response = self.client.delete(reverse('inventory_api:tag', args=(tag.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_delete_tag(self):
        tag = Tag.objects.create(name=get_random_string(12))
        self._set_permissions("inventory.delete_tag")
        response = self.client.delete(reverse('inventory_api:tag', args=(tag.pk,)))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Tag.objects.filter(pk=tag.pk).count(), 0)

    # list tag

    def test_list_tag_unauthorized(self):
        response = self.client.get(reverse('inventory_api:tags'))
        self.assertEqual(response.status_code, 403)

    def test_list_tag(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        taxonomy = Taxonomy.objects.create(name=get_random_string())
        tag = Tag.objects.create(
            taxonomy=taxonomy,
            meta_business_unit=meta_business_unit,
            name=get_random_string(12)
        )
        self._set_permissions("inventory.view_tag")
        response = self.client.get(reverse('inventory_api:tags'), {"name": tag.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0],
            {"id": tag.pk,
             "taxonomy": taxonomy.pk,
             "meta_business_unit": meta_business_unit.pk,
             "name": tag.name,
             "slug": tag.slug,
             "color": tag.color}
        )

    # create taxonomy

    def test_create_taxonomy_unauthorized(self):
        data = {"name": "TestTax01"}
        response = self.client.post(reverse('inventory_api:taxonomies'), data)
        self.assertEqual(response.status_code, 403)

    def test_create_taxonomy(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string(12))
        data = {'meta_business_unit': meta_business_unit.pk, 'name': 'TestTax0'}
        self._set_permissions("inventory.add_taxonomy")
        response = self.client.post(reverse('inventory_api:taxonomies'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        taxonomy = Taxonomy.objects.get(name='TestTax0')
        self.assertEqual(taxonomy.meta_business_unit, meta_business_unit)
        self.assertEqual(taxonomy.name, data["name"])
        self.assertEqual(
            response.data,
            {"id": taxonomy.pk,
             "meta_business_unit": meta_business_unit.pk,
             "name": taxonomy.name,
             "created_at": taxonomy.created_at.isoformat(),
             "updated_at": taxonomy.updated_at.isoformat()}
        )

    # get taxonomy

    def test_get_taxonomy_unauthorized(self):
        taxonomy = Taxonomy.objects.create(name=get_random_string(12))
        response = self.client.get(reverse('inventory_api:taxonomy', args=(taxonomy.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_get_taxonomy(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        taxonomy = Taxonomy.objects.create(meta_business_unit=meta_business_unit, name=get_random_string())
        self._set_permissions("inventory.view_taxonomy")
        response = self.client.get(reverse('inventory_api:taxonomy', args=(taxonomy.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"id": taxonomy.pk,
             "meta_business_unit": meta_business_unit.pk,
             "name": taxonomy.name,
             "created_at": taxonomy.created_at.isoformat(),
             "updated_at": taxonomy.updated_at.isoformat()}
        )

    # update taxonomy

    def test_update_taxonomy_unauthorized(self):
        taxonomy = Taxonomy.objects.create(name=get_random_string(12))
        response = self.client.put(reverse('inventory_api:taxonomy', args=(taxonomy.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_update_taxonomy(self):
        taxonomy = Taxonomy.objects.create(name=get_random_string(12))
        self._set_permissions("inventory.change_taxonomy")
        url = reverse('inventory_api:taxonomy', args=(taxonomy.pk,))
        updated_name = get_random_string(12)
        data = {'name': updated_name}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        taxonomy.refresh_from_db()
        self.assertEqual(taxonomy.name, updated_name)

    def test_update_taxonomy_name_error(self):
        name = get_random_string(12)
        Taxonomy.objects.create(name=name)
        taxonomy = Taxonomy.objects.create(name=get_random_string())
        self._set_permissions("inventory.change_taxonomy")
        url = reverse('inventory_api:taxonomy', args=(taxonomy.pk,))
        data = {'name': name}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"name": ["taxonomy with this name already exists."]})

    # delete taxonomy

    def test_delete_taxonomy_unauthorized(self):
        taxonomy = Taxonomy.objects.create(name=get_random_string(12))
        response = self.client.delete(reverse('inventory_api:taxonomy', args=(taxonomy.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_delete_taxonomy(self):
        taxonomy = Taxonomy.objects.create(name=get_random_string(12))
        self._set_permissions("inventory.delete_taxonomy")
        response = self.client.delete(reverse('inventory_api:taxonomy', args=(taxonomy.pk,)))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Taxonomy.objects.filter(pk=taxonomy.pk).count(), 0)

    # list taxonomy

    def test_list_taxonomy_unauthorized(self):
        response = self.client.get(reverse('inventory_api:taxonomies'))
        self.assertEqual(response.status_code, 403)

    def test_list_taxonomy(self):
        meta_business_unit = MetaBusinessUnit.objects.create(name=get_random_string())
        taxonomy = Taxonomy.objects.create(
            meta_business_unit=meta_business_unit,
            name=get_random_string(12)
        )
        self._set_permissions("inventory.view_taxonomy")
        response = self.client.get(reverse('inventory_api:taxonomies'), {"name": taxonomy.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0],
            {"id": taxonomy.pk,
             "meta_business_unit": meta_business_unit.pk,
             "name": taxonomy.name,
             "created_at": taxonomy.created_at.isoformat(),
             "updated_at": taxonomy.updated_at.isoformat()}
        )
