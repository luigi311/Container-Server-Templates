# Container-Server-Templates

Generates Docker Compose YAML files for various applications using multiple sources. It allows updating templates, listing available applications, and creating the necessary Docker Compose files for each application.

## Features

- **Generate Docker Compose Files:** Create `docker-compose.yml` files for applications based on provided templates.
- **List Applications:** List all available applications and their respective authors.

## Sources

- [x] Unraid
- [ ] Offical application sources

## Requirements

- Python 3.x

## Setup

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install Dependencies:**
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create a `.env` File:**
   ```env
   DOCKER_COMPOSE_FOLDER=Docker_Compose
   UNRAID_REPO_FOLDER=./Unraid_Repositories
   UNRAID_REPOSITORY_LIST=https://raw.githubusercontent.com/Squidly271/AppFeed/master/repositoryList.json
   UNRAID_REPOSITORIES=<optional-custom-repositories>
   ```

## Usage

### Command Line Arguments

- **Update Templates:**
  Update templates from the repository list.
  ```bash
  python main.py --update_templates
  ```

- **List Applications:**
  List all available applications.
  ```bash
  python main.py --list
  ```

## Error Handling

The program includes basic error handling to catch and print exceptions and stack traces.

## Contribution

Feel free to fork the repository and submit pull requests for improvements or bug fixes. Ensure to follow best practices and include appropriate documentation for any changes made.
