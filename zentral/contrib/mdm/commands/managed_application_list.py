import logging
from zentral.contrib.mdm.models import Channel, DeviceArtifact, Platform, TargetArtifactStatus
from .base import register_command, Command


logger = logging.getLogger("zentral.contrib.mdm.commands.managed_application_list")


class ManagedApplicationList(Command):
    request_type = "ManagedApplicationList"
    reschedule_notnow = True

    @staticmethod
    def verify_channel_and_device(channel, enrolled_device):
        return (
            (
                channel == Channel.Device
                or enrolled_device.platform == Platform.macOS.name
            ) and (
                not enrolled_device.user_enrollment
                or enrolled_device.platform in (Platform.iOS.name, Platform.macOS.name)
            )
        )

    def load_kwargs(self):
        self.identifiers = self.db_command.kwargs.get("identifiers", [])
        self.retries = self.db_command.kwargs.get("retries", 0)
        self.store_result = not self.identifiers

    def build_command(self):
        command = {}
        if self.identifiers:
            command["Identifiers"] = self.identifiers
        return command

    def _update_device_artifact(self):
        found = True
        error = False
        installed = True
        application_list = self.response.get("ManagedApplicationList", {})  # it is a dict!!!
        for identifier in self.identifiers:
            app = application_list.get(identifier)
            if not app:
                found = False
                installed = False
                continue
            status = app.get("Status")
            if status in ("Managed", "UserInstalledApp"):
                continue
            installed = False
            if status in ("Failed", "ManagedButUninstalled", "UserRejected", "UpdateRejected"):
                error = True

        if found and installed:
            # cleanup
            (DeviceArtifact.objects.filter(enrolled_device=self.enrolled_device,
                                           artifact_version__artifact=self.artifact)
                                   .exclude(artifact_version=self.artifact_version)
                                   .delete())
            # update
            DeviceArtifact.objects.update_or_create(
                enrolled_device=self.enrolled_device,
                artifact_version=self.artifact_version,
                defaults={"status": TargetArtifactStatus.Installed.name}
            )
        elif error:
            # we remove the device artifact, a new install will be triggered
            # TODO evaluate if it is the best option
            # cleanup
            DeviceArtifact.objects.filter(enrolled_device=self.enrolled_device,
                                          artifact_version=self.artifact_version).delete()
        elif self.retries >= 10:  # TODO hardcoded
            logger.warning("Stop rescheduling %s command on device %s for artifact version %s.",
                           self.request_type,
                           self.enrolled_device.serial_number,
                           self.artifact_version.pk)
        else:
            if not found:
                logger.warning("Artifact version %s was not found on device %s.",
                               self.artifact_version.pk, self.enrolled_device.serial_number)
            # found, without error, retries <= max
            # queue a new managed application list command
            delay_seconds = 15  # TODO hardcoded
            self.create_for_device(
                self.enrolled_device,
                self.artifact_version,
                kwargs={"identifiers": self.identifiers,
                        "retries": self.retries + 1},
                queue=True, delay=delay_seconds
            )

    def command_acknowledged(self):
        if self.artifact_version and self.identifiers:
            self._update_device_artifact()


register_command(ManagedApplicationList)
