from __future__ import annotations
from glob import glob
import os
import typing as t
import pkg_resources

from .__about__ import __version__

from tutor import config as tutor_config
from tutor import exceptions
from tutor import hooks as tutor_hooks



config = {
    "unique": {
        "HOOK_SECRET": "{{ 20|random_string }}",
        "SECRET_KEY": "{{ 20|random_string }}",
        "MYSQL_PASSWORD": "{{ 12|random_string }}",
    },
    "defaults": {
        "VERSION": __version__,
        "DOCKER_IMAGE": "{{ DOCKER_REGISTRY }}fundocker/openedx-richie:{{ RICHIE_VERSION }}",
        "RELEASE_VERSION": "v2.23.0",
        "HOST": "courses.{{ LMS_HOST }}",
        "MYSQL_DATABASE": "richie",
        "MYSQL_USERNAME": "richie",
        "ELASTICSEARCH_INDICES_PREFIX": "richie",
    },
}


# Initialization hooks

# To add a custom initialization task, create a bash script template under:
# tutorcodejail/templates/codejail/tasks/
# and then add it to the MY_INIT_TASKS list. Each task is in the format:
# ("<service>", ("<path>", "<to>", "<script>", "<template>"))
MY_INIT_TASKS: list[tuple[str, tuple[str, ...]]] = [
    ("mysql", ("richie", "tasks", "mysql", "init")),
    ("richie", ("richie", "tasks", "richie", "init")),
    ("richie-openedx", ("richie", "tasks", "richie-openedx", "init")),
]

# Initialization hooks
for service, template_path in MY_INIT_TASKS:
    full_path: str = pkg_resources.resource_filename(
        "tutorrichie", os.path.join("templates", *template_path)
    )
    with open(full_path, encoding="utf-8") as init_task_file:
        init_task: str = init_task_file.read()
    tutor_hooks.Filters.CLI_DO_INIT_TASKS.add_item((service, init_task))


# Image management
tutor_hooks.Filters.IMAGES_BUILD.add_item((
    "richie",
    ("plugins", "richie", "build", "richie"),
    "{{ RICHIE_DOCKER_IMAGE }}",
    (),
))
tutor_hooks.Filters.IMAGES_PULL.add_item((
    "richie",
    "{{ RICHIE_DOCKER_IMAGE }}",
))
tutor_hooks.Filters.IMAGES_PUSH.add_item((
    "richie",
    "{{ RICHIE_DOCKER_IMAGE }}",
))


@tutor_hooks.Filters.COMPOSE_MOUNTS.add()
def _mount_richie(volumes, name):
    """
    When mounting richie with `--mount=/path/to/richie`,
    bind-mount the host repo in the notes container.
    """
    if name == "richie":
        path = "/app/richie"
        volumes += [
            ("richie", path),
            ("richie-job", path),
        ]
    return volumes


tutor_hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    pkg_resources.resource_filename("tutorrichie", "templates")
)

tutor_hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("richie/build", "plugins"),
        ("richie/apps", "plugins"),
    ],
)

# Load patches from files
for path in glob(
    os.path.join(
        pkg_resources.resource_filename("tutorrichie", "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        tutor_hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read())
        )
 
# Add configuration entries
tutor_hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        (f"RICHIE_{key}", value)
        for key, value in config.get("defaults", {}).items()
    ]
)
tutor_hooks.Filters.CONFIG_UNIQUE.add_items(
    [
        (f"RICHIE_{key}", value)
        for key, value in config.get("unique", {}).items()
    ]
)
tutor_hooks.Filters.CONFIG_OVERRIDES.add_items(
    list(config.get("overrides", {}).items())
)


@tutor_hooks.Filters.APP_PUBLIC_HOSTS.add()
def _notes_public_hosts(hosts: list[str], context_name: t.Literal["local", "dev"]) -> list[str]:
    if context_name == "dev":
        hosts += ["courses.{{ LMS_HOST }}:8003"]
    else:
        hosts += ["{{ RICHIE_HOST }}"]
    return hosts