import os
import re
import json
import logging
from packaging.version import Version
from datetime import datetime

def parse_version(version_string):
    """Parse version string into numerical version and additional info."""
    logging.debug(f"Parsing version from string: {version_string}")
    match = re.match(r'(\d+\.\d+\.\d+\.\d+)(.*)', version_string)
    if match:
        numerical_version = match.group(1)
        additional_info = match.group(2).strip('-')
        logging.debug(f"Extracted version: {numerical_version}, additional info: {additional_info}")
        return Version(numerical_version), additional_info
    logging.debug(f"Failed to parse version from string: {version_string}")
    return None, version_string

def load_json_file(file_path):
    """Load a JSON file and return the data."""
    with open(file_path, 'r') as file:
        return json.load(file)

def find_component_name(filename, component_mapping):
    """Find the component name based on the filename using the mapping."""
    logging.debug(f"Buscando el componente : {filename}")
    for component, filenames in component_mapping.items():
        if filename in filenames:
            logging.debug(f"Match con el componente: {component} y el archivo : {filename}")
            return component
    logging.debug(f"No se encuentra el archivo: {filename}")
    return None

def is_version_in_range(version, from_version, to_version):
    """Check if a version is within the specified range."""
    if from_version and version < from_version:
        return False
    if to_version and version > to_version:
        return False
    return True

def find_version_directories(base_path, from_version=None, to_version=None):
    """Find all version directories within the specified range."""
    version_dirs = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            numerical_version, _ = parse_version(item)
            if numerical_version and is_version_in_range(numerical_version, from_version, to_version):
                version_dirs.append(item_path)
    return version_dirs

def find_latest_versions(base_path, component_mapping, components_to_search, from_version=None, to_version=None):
    """Find the latest versions of each component in the directory structure."""
    components = {}
    version_dirs = find_version_directories(base_path, from_version, to_version)
    total_dirs = len(version_dirs)
    
    logging.info(f"Analizando {total_dirs} directorios de versiones desde {from_version} hasta {to_version}")

    def process_directory(current_path, parent_version=None, parent_info=None):
        """Recursively process directories to find component versions."""
        logging.debug(f"Processing directory: {current_path}")
        try:
            items = os.listdir(current_path)
            logging.debug(f"Contents of {current_path}: {items}")

            # Extract version from the current directory name if not already provided by parent
            if parent_version is None or parent_info is None:
                current_dir_name = os.path.basename(current_path)
                numerical_version, additional_info = parse_version(current_dir_name)
                if numerical_version:
                    parent_version, parent_info = numerical_version, additional_info

            # Skip processing if version is out of range
            if parent_version and not is_version_in_range(parent_version, from_version, to_version):
                logging.debug(f"Skipping directory {current_path} with version {parent_version}")
                return

            # Process subdirectories first
            for item in items:
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    logging.debug(f"Processing subdirectory: {item_path}")
                    process_directory(item_path, parent_version, parent_info)

            # Then process files in the current directory
            for item in items:
                item_path = os.path.join(current_path, item)
                if os.path.isfile(item_path):
                    component_name = find_component_name(item, component_mapping)
                    if component_name and (components_to_search == "all" or component_name in components_to_search):
                        logging.debug(f"File found: {item} in {current_path} with version {parent_version}")
                        if component_name not in components:
                            components[component_name] = (parent_version, parent_info, current_path)
                        else:
                            current_numerical_version, current_additional_info, current_directory = components[component_name]
                            if (parent_version > current_numerical_version or
                                (parent_version == current_numerical_version and parent_info > current_additional_info)):
                                components[component_name] = (parent_version, parent_info, current_path)

        except Exception as e:
            logging.error(f"Error procesando el directorio {current_path}: {e}")

    for version_dir in version_dirs:
        process_directory(version_dir)

    logging.info(f"Se han analizado {total_dirs} directorios de versiones")
    return components

def generate_report(components, output_file):
    """Generate a report of the latest versions of each component."""
    report_lines = [
        "Directory\t\tComponent\t\tLatest Version\t\tAdditional Info",
        "---------\t\t---------\t\t-------------\t\t---------------"
    ]
    for component, (version, additional_info, directory) in sorted(components.items()):
        version_str = version if version else "None"
        additional_info_str = additional_info if additional_info else "None"
        line = f"{directory}\t\t{component}\t\t{version_str}\t\t{additional_info_str}"
        report_lines.append(line)

    report_content = "\n".join(report_lines)

    # Print to console
    #print(report_content)

    # Write to output file
    with open(output_file, 'w') as file:
        file.write(report_content)

if __name__ == "__main__":
    config_path = "./config/user_config.json"  # Path to the user configuration file
    component_mapping_path = "./config/component_mapping.json"  # Path to the component mapping configuration file
    customers_config_path = "./config/customers.json"  # Path to the customers configuration file

    user_config = load_json_file(config_path)
    base_path = user_config.get("base_path")
    components_to_search = user_config.get("components", "all")
    output_file_name = user_config.get("output_file", "output_report.txt")
    output_file = os.path.join("./output", output_file_name)
    log_file_name = user_config.get("log_file", "application.log")
    log_file = os.path.join("./logs", log_file_name)
    log_level_str = user_config.get("log_level", "INFO").upper()
    from_version_str = user_config.get("from_version")
    to_version_str = user_config.get("to_version")
    customer = user_config.get("customer")

    # Parse versions
    from_version = Version(from_version_str) if from_version_str else None
    to_version = Version(to_version_str) if to_version_str else None

    # Configuración del logging
    logging.basicConfig(
        filename=log_file,
        level=getattr(logging, log_level_str, logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    start_time = datetime.now()
    logging.info("Inicio de la ejecución del script")
    logging.info(f"Hora de inicio: {start_time}")

    logging.info(f"Archivo de configuración del usuario: {config_path}")
    logging.info(f"Archivo de configuración de mapeo de componentes: {component_mapping_path}")
    logging.info(f"Ruta base para la búsqueda de archivos: {base_path}")
    logging.info(f"Componentes a buscar: {components_to_search}")
    logging.info(f"Archivo de salida: {output_file}")
    logging.info(f"Archivo de log: {log_file}")
    logging.info(f"Desde versión: {from_version_str}")
    logging.info(f"Hasta versión: {to_version_str}")

    # Load component mapping and customer configurations
    component_mapping = load_json_file(component_mapping_path)
    customers_config = load_json_file(customers_config_path)

    # Check if customer parameter is present and valid
    if customer and customer in customers_config:
        logging.info(f"Cliente '{customer}' encontrado. Sobreescribiendo los componentes a buscar.")
        components_to_search = customers_config[customer]
    else:
        logging.info(f"Cliente '{customer}' no encontrado o no especificado. Usando componentes desde la configuracion general.")

    if components_to_search == "all" or "all" in components_to_search:
        logging.info("Components to search set to 'all'. Using all components from component mapping.")
        components_to_search = list(component_mapping.keys())

    components = find_latest_versions(base_path, component_mapping, components_to_search, from_version, to_version)
    generate_report(components, output_file)

    end_time = datetime.now()
    logging.info(f"Hora de finalización: {end_time}")
    logging.info(f"Duración total de la ejecución: {end_time - start_time}")
    logging.info("Fin de la ejecución del script")