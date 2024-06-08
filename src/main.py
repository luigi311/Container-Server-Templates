import os, re, json, traceback, argparse

from dotenv import load_dotenv
from difflib import get_close_matches

from src.unraid_templates import Unraid

load_dotenv(override=True)

DOCKER_COMPOSE_FOLDER = os.getenv("DOCKER_COMPOSE_FOLDER", "Docker_Compose")


def generate_docker_yaml(app_name: str, template: json):
    # Cleanup app_name and remove unsupported characters
    app_name = re.sub(r"[^a-zA-Z0-9_-]", "", app_name).lower()
    description = template.get("description")
    if description:
        description.replace("\n", "\n# ").replace("\r", "")
        # Remove new lines of just # from description
        description = re.sub(r"^#(\s+)?$", "", description, flags=re.MULTILINE)
        # Remove empty lines from description
        description = re.sub(r"^\s*$\n", "", description, flags=re.MULTILINE)

    docker_compose_yaml = f"# {description}\n\n"

    docker_compose_yaml += f"""
services:
  {app_name}:
    image: {template['image']}
    container_name: {app_name}
    restart: unless-stopped
    network_mode: {template['network_mode']}
"""

    if template.get("post_arguments"):
        docker_compose_yaml += "    command: "
        docker_compose_yaml += f'{template["post_arguments"]}'
        docker_compose_yaml += "\n"

    docker_compose_yaml += "    ports:"
    if template.get("ports"):
        for port in template["ports"]:
            target = template["ports"][port]["Target"]
            default = template["ports"][port]["Default"]
            description = (
                template["ports"][port]["Description"]
                .replace("\n", "\n      # ")
                .replace("\r", "")
            )

            docker_compose_yaml += (
                f"\n      # {port} {description}\n      - {default}:{target}"
            )
        docker_compose_yaml += "\n"
    else:
        docker_compose_yaml += " []\n"

    docker_compose_yaml += "    environment:"
    if template.get("environment"):
        for variable in template["environment"]:
            target = template["environment"][variable]["Target"]
            default = template["environment"][variable]["Default"]
            description = template["environment"][variable].get("Description")
            if description:
                description.replace("\n", "\n      # ").replace("\r", "")

            docker_compose_yaml += (
                f"\n      # {variable} {description}\n      - {target}={default}"
            )
        docker_compose_yaml += "\n"
    else:
        docker_compose_yaml += " []\n"

    docker_compose_yaml += "    volumes:"
    if template.get("volumes"):
        for volume in template["volumes"]:
            target = template["volumes"][volume]["Target"]
            default = template["volumes"][volume]["Default"]
            description = template["volumes"][volume].get("Description")
            if description:
                description.replace("\n", "\n      # ").replace("\r", "")

            docker_compose_yaml += (
                f"\n      # {volume} {description}\n      - {default}:{target}"
            )
        docker_compose_yaml += "\n"
    else:
        docker_compose_yaml += " []\n"

    docker_compose_yaml += "    labels:"
    if template.get("labels"):
        for label in template["labels"]:
            target = template["labels"][label]["Target"]
            default = template["labels"][label]["Default"]
            description = template["labels"][label].get("Description")
            if description:
                description.replace("\n", "\n      # ").replace("\r", "")

            docker_compose_yaml += (
                f"\n      # {label} {description}\n      - {target}={default}"
            )
        docker_compose_yaml += "\n"
    else:
        docker_compose_yaml += " []\n"

    docker_compose_yaml += "    devices:"
    if template.get("devices"):
        for device in template["devices"]:
            target = template["devices"][device]["Target"]
            default = template["devices"][device]["Default"]
            description = template["devices"][device].get("Description")
            if description:
                description.replace("\n", "\n      # ").replace("\r", "")

            docker_compose_yaml += (
                f"\n      # {device} {description}\n      - {target}:{default}"
            )
        docker_compose_yaml += "\n"
    else:
        docker_compose_yaml += " []\n"

    return docker_compose_yaml


def create_app_docker_compose(folder: str, app_name: str, template: json):
    docker_compose_yaml = generate_docker_yaml(app_name, template)

    if not os.path.exists(f"{folder}"):
        os.makedirs(f"{folder}", exist_ok=True)

    docker_file_path = f"{folder}/docker-compose.yml"
    if os.path.exists(docker_file_path):
        print(f"docker-compose.yml file already exists at {docker_file_path}")
        print("Moving current file to docker-compose.yml.old")

        if os.path.exists(f"{docker_file_path}.old"):
            os.remove(f"{docker_file_path}.old")

        os.rename(docker_file_path, f"{docker_file_path}.old")

    with open(docker_file_path, "w") as f:
        f.write(docker_compose_yaml)

    print(f"Created {docker_file_path}")


def load_templates(folder: str):
    templates = {}

    # Load folder/templates.json
    if os.path.exists(f"{folder}/templates.json"):
        with open(f"{folder}/templates.json", "r") as f:
            templates = json.load(f)

    return templates


def save_templates(folder: str, templates: dict):
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    # Save templates to templates.json
    with open(f"{folder}/templates.json", "w") as f:
        json.dump(templates, f, indent=4, sort_keys=True)


def update_templates():
    # Get Unraid templates
    unraid = Unraid(
        repo_folder=os.getenv("UNRAID_REPO_FOLDER", "./Unraid_Repositories"),
        repositoryList=os.getenv(
            "UNRAID_REPOSITORY_LIST",
            "https://raw.githubusercontent.com/Squidly271/AppFeed/master/repositoryList.json",
        ),
        repositories=os.getenv("UNRAID_REPOSITORIES", None),
    )

    unraid.update_repos()
    unraid.update_templates()

    templates = unraid.templates

    save_templates(DOCKER_COMPOSE_FOLDER, templates)

    return templates


def create_all_apps_docker_compose(folder: str, templates: dict):
    for app, authors in templates.items():
        for author, template in authors.items():
            print(f"Creating {app} by {author}")
            app_folder = f"{folder}/{app}/{author}"
            create_app_docker_compose(app_folder, app, template)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Create templates for Container-Server"
    )
    parser.add_argument(
        "--update_templates",
        action="store_true",
        help="Update templates from repositoryList and repositories",
    )
    parser.add_argument("--list", action="store_true", help="List apps")
    args = parser.parse_args()

    return args


def generate_app_list(folder: str):
    if not os.path.exists(folder):
        return []

    app_list = {}

    # for each folder in folder
    for app in os.listdir(folder):
        if os.path.isdir(f"{folder}/{app}"):
            app_list[app] = []

            # for each folder in app
            for author in os.listdir(f"{folder}/{app}"):
                if os.path.isdir(f"{folder}/{app}/{author}"):
                    app_list[app].append(author)

    # Write app_list.json to folder
    with open(f"{folder}/app_list.json", "w") as f:
        json.dump(app_list, f, indent=4, sort_keys=True)


def main():
    try:
        args = arg_parser()

        templates = load_templates(DOCKER_COMPOSE_FOLDER)
        updated = False
        if not templates:
            updated = True
            templates = update_templates()

        if args.update_templates:
            # Do not update templates if they were just updated
            if not updated:
                templates = update_templates()

        if args.list:
            print("List of apps:")
            for app in templates.keys():
                print(f"  {app}")
        else:
            create_all_apps_docker_compose(DOCKER_COMPOSE_FOLDER, templates)
            generate_app_list(DOCKER_COMPOSE_FOLDER)

    except Exception as error:
        if isinstance(error, list):
            for message in error:
                print(message)
        else:
            print(error)

        print(traceback.format_exc())

    except KeyboardInterrupt:
        print("Exiting...")
        os._exit(0)
