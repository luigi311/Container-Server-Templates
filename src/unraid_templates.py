import json, requests, os, git, xmltodict

exclude_xmls = ["ca_profile.xml"]
exclude_dirs = [".git", ".github", "issues", "depricated", ".history", ".idea"]


def get_repositoryList(repositoryList: str):
    # Request repositoryList.json from url and parse it into a dictionary
    repositoryListJson = json.loads(requests.get(repositoryList).text)

    repositories = []
    for repository in repositoryListJson:
        repositories.append(repository["url"])

    return repositories


def parse_new_config(variables: dict, name: str, user: str, config: dict):
    config_type = config.get("@Type")
    config_name = config.get("@Name")
    if not config_name:
        config_name = config.get("@Target")

    if config_type == "Port":
        variables[name][user]["ports"][config_name] = {
            "Target": config.get("@Target"),
            "Default": config.get("@Default"),
            "Description": config.get("@Description"),
        }
    elif config_type == "Path":
        variables[name][user]["volumes"][config_name] = {
            "Target": config.get("@Target"),
            "Default": config.get("@Default"),
            "Description": config.get("@Description"),
            "Mode": config.get("@Mode"),
        }
    elif config_type == "Variable":
        variables[name][user]["environment"][config_name] = {
            "Target": config.get("@Target"),
            "Default": config.get("@Default"),
            "Description": config.get("@Description"),
        }
    elif config_type == "Device":
        variables[name][user]["devices"][config_name] = {
            "Target": config.get("@Target"),
            "Default": config.get("@Default"),
            "Description": config.get("@Description"),
        }
    elif config_type == "Label":
        variables[name][user]["labels"][config_name] = {
            "Target": config.get("@Target"),
            "Default": config.get("@Default"),
            "Description": config.get("@Description"),
        }
    else:
        print(f"Unknown config type {config.get('@Type')}")


def parse_template(template: str, user: str, file_name: str):
    try:
        # Parse template and return variables
        variables = {}
        data_dict = xmltodict.parse(template)
        app = (
            data_dict["Container"]
            if "Container" in data_dict
            else data_dict["Containers"]
        )

        # Get template name
        name = app.get("Name")

        variables[name] = {}
        variables[name][user] = {}

        # Get template repository
        variables[name][user]["image"] = app.get("Repository")

        # If not name or image, skip
        if not name or not variables[name][user]["image"]:
            return

        # Get template description
        variables[name][user]["description"] = app.get("Overview")

        # Default network mode to bridge
        variables[name][user]["network_mode"] = "bridge"

        # Get template network type
        if app.get("Network"):
            variables[name][user]["network_mode"] = app.get("Network")
        else:
            networking = app.get("Networking")
            if networking:
                variables[name][user]["network_mode"] = networking.get("Mode")

        # Extra Parameters
        variables[name][user]["extra_parameters"] = app.get("ExtraParams")
        # Post Arguments
        variables[name][user]["post_arguments"] = app.get("PostArgs")

        variables[name][user]["ports"] = {}
        variables[name][user]["volumes"] = {}
        variables[name][user]["environment"] = {}
        variables[name][user]["labels"] = {}
        variables[name][user]["devices"] = {}

        # New template format
        if app.get("Config"):
            if isinstance(app["Config"], list):
                for config in app["Config"]:
                    parse_new_config(variables, name, user, config)
            else:
                parse_new_config(variables, name, user, app["Config"])

        # Old Template format
        else:
            if app.get("Networking") and app["Networking"].get("Publish"):
                if isinstance(app["Networking"]["Publish"]["Port"], list):
                    for port in app["Networking"]["Publish"]["Port"]:
                        variables[name][user]["ports"][port["ContainerPort"]] = {
                            "Target": port["ContainerPort"],
                            "Default": port.get("HostPort"),
                            "Description": "",
                        }
                else:
                    port = app["Networking"]["Publish"]["Port"]
                    variables[name][user]["ports"][port["ContainerPort"]] = {
                        "Target": port["ContainerPort"],
                        "Default": port.get("HostPort"),
                        "Description": "",
                    }

            if app.get("Data"):
                if isinstance(app["Data"]["Volume"], list):
                    for volume in app["Data"]["Volume"]:
                        variables[name][user]["volumes"][volume["ContainerDir"]] = {
                            "Target": volume["ContainerDir"],
                            "Default": volume.get("HostDir"),
                            "Description": "",
                            "Mode": volume.get("Mode"),
                        }
                else:
                    volume = app["Data"]["Volume"]
                    variables[name][user]["volumes"][volume["ContainerDir"]] = {
                        "Target": volume["ContainerDir"],
                        "Default": volume.get("HostDir"),
                        "Description": "",
                        "Mode": volume.get("Mode"),
                    }

            if app.get("Environment"):
                if isinstance(app["Environment"]["Variable"], list):
                    for variable in app["Environment"]["Variable"]:
                        variables[name][user]["environment"][variable["Name"]] = {
                            "Target": variable["Name"],
                            "Default": variable.get("Value"),
                            "Description": "",
                        }
                else:
                    variable = app["Environment"]["Variable"]
                    variables[name][user]["environment"][variable["Name"]] = {
                        "Target": variable["Name"],
                        "Default": variable.get("Value"),
                        "Description": "",
                    }

        return variables

    except Exception as error:
        print(f"Failed to parse template {file_name}: {error}")
        return


def get_xmls_from_dir(directory: str):
    xmls = []
    # Iterate through directory and subdirectories and add all xml files to xmls
    # excluding files named exclude_xmls and directories containing anything in exclude_dirs
    for file in os.listdir(directory):
        if os.path.isdir(f"{directory}/{file}"):
            # if directory contains anything in exclude_dirs ignoring case, skip it
            if any(exclude_dir.lower() in file.lower() for exclude_dir in exclude_dirs):
                continue
            xmls.extend(get_xmls_from_dir(f"{directory}/{file}"))
        elif file.endswith(".xml"):
            if file in exclude_xmls:
                continue
            xmls.append(f"{directory}/{file}")

    return xmls


# Parse Unraid templates and return variables for use in container creation
class Unraid:
    def __init__(
        self,
        repo_folder: str = "./Unraid_Repositories",
        repositoryList: str = None,
        repositories: list = None,
    ):
        self.repo_folder = repo_folder
        self.repo_file = f"{repo_folder}/unraid_repos.csv"
        self.template_file = f"{repo_folder}/unraid_templates.json"
        self.repositoryList = repositoryList
        self.repositories = repositories

        self.load_repos()
        self.load_templates()

    def save_repos(self):
        if not os.path.exists(self.repo_folder):
            os.makedirs(self.repo_folder, exist_ok=True)

        # Save repos to repos.csv
        with open(self.repo_file, "w") as f:
            for repo in self.repos:
                f.write(f"{repo}\n")

    def load_repos(self):
        self.repos = []
        if os.path.exists(self.repo_file):
            with open(self.repo_file, "r") as f:
                for line in f:
                    self.repos.append(line.strip())

    def update_repos(self):
        self.repos = []
        if self.repositoryList:
            self.repos.extend(get_repositoryList(self.repositoryList))

        if self.repositories:
            if type(self.repositories) == str:
                repositories = self.repositories.split(",")

            if type(repositories) == list:
                for repository in repositories:
                    self.repos.append(repository)

        self.save_repos()

    def save_templates(self):
        if not os.path.exists(self.repo_folder):
            os.makedirs(self.repo_folder, exist_ok=True)

        # Save templates to templates.json
        with open(self.template_file, "w") as f:
            json.dump(self.templates, f, indent=4, sort_keys=True)

    def load_templates(self):
        if os.path.exists(self.template_file):
            print(f"Loading templates from {self.template_file}")
            with open(self.template_file, "r") as f:
                self.templates = json.load(f)
        else:
            self.templates = {}

    def update_templates(self):
        self.templates = {}
        xmls = {}
        for repo in self.repos:
            # Cloning the repository if it doesn't exist
            try:
                # Get repo up to name only removing everything passed the 5th /
                split_repo = repo.split("/")[0:5]
                clean_repo = "/".join(split_repo)
                user, name = repo.split("/")[3:5]
                repo_path = f"{self.repo_folder}/{user}/{name}"

                if os.path.exists(repo_path):
                    print(f"Updating {user}/{name}")
                    git.Repo(repo_path).remotes.origin.pull()
                else:
                    # Create directory if it doesn't exist
                    os.makedirs(repo_path, exist_ok=True)

                    print(f"Cloning {user}/{name}")
                    git.Repo.clone_from(clean_repo, repo_path)

                if user not in xmls:
                    xmls[user] = []

                xmls[user].extend(get_xmls_from_dir(repo_path))
            except:
                print(f"Failed to clone {repo}")
                continue

        for user in xmls:
            for xml in xmls[user]:
                try:
                    with open(xml, "r") as f:
                        template_str = f.read()

                    template = parse_template(template_str, user, xml)
                    if template:
                        self.templates.update(template)

                except Exception as error:
                    continue

        self.save_templates()
