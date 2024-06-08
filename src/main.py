import os
import re
import json
import traceback
import argparse
from dotenv import load_dotenv
from difflib import get_close_matches
from src.unraid_templates import Unraid

load_dotenv(override=True)
DOCKER_COMPOSE_FOLDER = os.getenv("DOCKER_COMPOSE_FOLDER", "Docker_Compose")


def clean_description(description):
    if description:
        description = description.replace("\n", "\n# ").replace("\r", "")
        description = re.sub(r"^#(\s+)?$", "", description, flags=re.MULTILINE)
        description = re.sub(r"^\s*$\n", "", description, flags=re.MULTILINE)
    return description


def format_section(section_name, items, format_string):
    section = f"    {section_name}:"
    if items:
        for key, item in items.items():
            description = clean_description(item.get("Description"))
            section += format_string.format(key=key, item=item, description=description)
        section += "\n"
    else:
        section += " []\n"
    return section


def generate_docker_yaml(app_name, template):
    app_name = re.sub(r"[^a-zA-Z0-9_-]", "", app_name).lower()
    description = clean_description(template.get("description", ""))

    docker_compose_yaml = f"# {description}\n\nservices:\n  {app_name}:\n"
    docker_compose_yaml += f"    image: {template['image']}\n    container_name: {app_name}\n    restart: unless-stopped\n    network_mode: {template['network_mode']}\n"

    if template.get("post_arguments"):
        docker_compose_yaml += f"    command: {template['post_arguments']}\n"

    docker_compose_yaml += format_section(
        "ports",
        template.get("ports"),
        "\n      # {key} {description}\n      - {item[Default]}:{item[Target]}",
    )
    docker_compose_yaml += format_section(
        "environment",
        template.get("environment"),
        "\n      # {key} {description}\n      - {item[Target]}={item[Default]}",
    )
    docker_compose_yaml += format_section(
        "volumes",
        template.get("volumes"),
        "\n      # {key} {description}\n      - {item[Default]}:{item[Target]}",
    )
    docker_compose_yaml += format_section(
        "labels",
        template.get("labels"),
        "\n      # {key} {description}\n      - {item[Target]}={item[Default]}",
    )
    docker_compose_yaml += format_section(
        "devices",
        template.get("devices"),
        "\n      # {key} {description}\n      - {item[Target]}:{item[Default]}",
    )

    return docker_compose_yaml


def sanitize_name(name):
    return re.sub(r"[^a-zA-Z0-9_ -]", "", name)


def create_app_docker_compose(folder, app_name, template):
    app_name = sanitize_name(app_name)
    docker_compose_yaml = generate_docker_yaml(app_name, template)
    os.makedirs(folder, exist_ok=True)

    docker_file_path = f"{folder}/docker-compose.yml"
    if os.path.exists(docker_file_path):
        print(f"docker-compose.yml file already exists at {docker_file_path}")
        os.replace(docker_file_path, f"{docker_file_path}.old")

    with open(docker_file_path, "w") as f:
        f.write(docker_compose_yaml)

    print(f"Created {docker_file_path}")


def load_templates(folder):
    templates_path = os.path.join(folder, "templates.json")
    if os.path.exists(templates_path):
        with open(templates_path, "r") as f:
            return json.load(f)
    return {}


def save_templates(folder, templates):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "templates.json"), "w") as f:
        json.dump(templates, f, indent=4, sort_keys=True)


def update_templates():
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


def create_all_apps_docker_compose(folder, templates):
    for app, authors in templates.items():
        for author, template in authors.items():
            print(f"Creating {app} by {author}")
            app_folder = os.path.join(folder, sanitize_name(app), sanitize_name(author))
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
    return parser.parse_args()


def generate_app_list(folder):
    # Create json file with list of apps and authors and the structure of the folder
    app_list = {}
    app_list["apps"] = []
    app_list["authors"] = []
    app_list["folder_structure"] = {}

    for app in os.listdir(folder):
        app_list["apps"].append(app)
        app_list["folder_structure"][app] = []

        app_path = os.path.join(folder, app)
        if os.path.isdir(app_path):
            for author in os.listdir(app_path):
                app_list["folder_structure"][app].append(author)
                app_list["authors"].append(author)

    # Remove duplicates
    app_list["apps"] = list(set(app_list["apps"]))
    app_list["authors"] = list(set(app_list["authors"]))

    with open(os.path.join(folder, "app_list.json"), "w") as f:
        json.dump(app_list, f, indent=4, sort_keys=True)


def main():
    try:
        args = arg_parser()
        templates = load_templates(DOCKER_COMPOSE_FOLDER) or update_templates()

        if args.update_templates and not templates:
            templates = update_templates()

        if args.list:
            print("List of apps:")
            for app in templates.keys():
                print(f"  {app}")
        else:
            create_all_apps_docker_compose(DOCKER_COMPOSE_FOLDER, templates)
            generate_app_list(DOCKER_COMPOSE_FOLDER)

    except Exception as error:
        print(error)
        print(traceback.format_exc())
    except KeyboardInterrupt:
        print("Exiting...")
        os._exit(0)


if __name__ == "__main__":
    main()
