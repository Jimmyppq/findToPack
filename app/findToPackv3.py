import os
import re
import json
import logging
from packaging.version import Version, InvalidVersion
from datetime import datetime

def parse_version(version_string):
    """Parse version string into numerical version and additional info."""
    logging.debug(f"Analizando la versión desde la cadena: {version_string}")
    match = re.match(r'(\d+\.\d+\.\d+\.\d+)(.*)', version_string)
    if match:
        numerical_version = match.group(1)
        additional_info = match.group(2).strip('-')
        logging.debug(f"Versión extraída: {numerical_version}, información adicional: {additional_info}")
        return Version(numerical_version), additional_info
    logging.debug(f"No se pudo analizar la versión desde la cadena: {version_string}")
    return None, version_string

def load_json_file(file_path):
    """Load a JSON file and return the data."""
    with open(file_path, 'r') as file:
        return json.load(file)

def find_component_name(filename, component_mapping):
    """Find the component name based on the filename using the mapping."""
    logging.debug(f"Buscando el nombre del componente para el archivo: {filename}")
    for component, filenames in component_mapping.items():
        if filename in filenames:
            logging.debug(f"Componente encontrado: {component} para el archivo: {filename}")
            return component
    logging.debug(f"No se encontró coincidencia para el archivo: {filename}")
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

def find_latest_versions(base_path, component_mapping, components_to_search, from_version=None, to_version=None, excluded_dirs=None):
    """Find the latest versions of each component in the directory structure."""
    components = {}
    version_dirs = find_version_directories(base_path, from_version, to_version)
    total_dirs = len(version_dirs)
    
    logging.info(f"Analizando {total_dirs} directorios de versiones desde {from_version} hasta {to_version}")
    logging.info(f"Iniciando búsqueda de componentes {components_to_search} ")

    def should_exclude_directory(directory_name):
        """Check if the directory should be excluded based on the configuration."""
        if excluded_dirs:
            for excluded in excluded_dirs:
                if excluded in directory_name:
                    return True
        return False

    def process_directory(current_path, parent_version=None, parent_info=None):
        """Recursively process directories to find component versions."""
        logging.debug(f"Procesando directorio: {current_path}")
        try:
            items = os.listdir(current_path)
            logging.debug(f"Contenido de {current_path}: {items}")

            # Extract version from the current directory name if not already provided by parent
            if parent_version is None or parent_info is None:
                current_dir_name = os.path.basename(current_path)
                numerical_version, additional_info = parse_version(current_dir_name)
                if numerical_version:
                    parent_version, parent_info = numerical_version, additional_info

            # Skip processing if version is out of range
            if parent_version and not is_version_in_range(parent_version, from_version, to_version):
                logging.debug(f"Omitiendo directorio {current_path} con versión {parent_version}")
                return

            # Process subdirectories first
            for item in items:
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    if should_exclude_directory(item):
                        logging.debug(f"Omitiendo subdirectorio: {item_path}")
                        continue
                    logging.debug(f"Procesando subdirectorio: {item_path}")
                    process_directory(item_path, parent_version, parent_info)

            # Then process files in the current directory
            for item in items:
                item_path = os.path.join(current_path, item)
                if os.path.isfile(item_path):
                    component_name = find_component_name(item, component_mapping)
                    if component_name and (components_to_search == "all" or component_name in components_to_search):
                        logging.debug(f"Archivo encontrado: {item} en {current_path} con versión {parent_version}")
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
        "Directorio\t\tComponente\t\tÚltima Versión\t\tInformación Adicional",
        "---------\t\t---------\t\t-------------\t\t---------------"
    ]
    for component, (version, additional_info, directory) in sorted(components.items()):
        version_str = version if version else "None"
        additional_info_str = additional_info if additional_info else "None"
        line = f"{directory}\t\t{component}\t\t{version_str}\t\t{additional_info_str}"
        report_lines.append(line)

    report_content = "\n".join(report_lines)

    output_file = os.path.splitext(output_file)[0] + ".txt"
    # Write to output file
    with open(output_file, 'w') as file:
        file.write(report_content)

def generate_report_html(components, output_file):
    """Generate a report of the latest versions of each component in HTML format."""
    
    report_lines = [
        "<html>",
        "<head><meta charset='UTF-8'><title>Report</title>",
        "<style>",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid black; padding: 8px; text-align: left; }",
        "th { background-color: #f2f2f2; }",
        "</style>",
        "</head>",
        "<body>",
        "<table border='0'>",
        "<tr><th>Directorio</th><th>Componente</th><th>Última Versión</th><th>Información Adicional</th></tr>"
    ]
    
    for component, (version, additional_info, directory) in sorted(components.items()):
        version_str = version if version else "None"
        additional_info_str = additional_info if additional_info else "None"
        line = f"<tr><td>{directory}</td><td>{component}</td><td>{version_str}</td><td>{additional_info_str}</td></tr>"
        report_lines.append(line)
    
    report_lines.append("</table>")
    report_lines.append("</body>")
    report_lines.append("</html>")
    
    report_content = "\n".join(report_lines)
    output_file = os.path.splitext(output_file)[0] + ".html"
    # Write to output file
    with open(output_file, 'w',encoding='utf-8') as file:
        file.write(report_content)

def write_dataconfig (logger,config_path,component_mapping_path,base_path,components_to_search,output_file,log_file,from_version_str,to_version_str,html):
    logger.info ("VERSION 3.9")
    logger.info(f"Archivo de configuración del usuario: {config_path}")
    logger.info(f"Archivo de configuración de mapeo de componentes: {component_mapping_path}")
    logger.info(f"Ruta base para la búsqueda de archivos: {base_path}")
    logger.info(f"Componentes a buscar: {components_to_search}")
    logger.info(f"Archivo de salida: {output_file}")
    logger.info(f"Archivo de log: {log_file}")
    logger.info(f"Desde versión: {from_version_str}")
    logger.info(f"Hasta versión: {to_version_str}")
    logger.info(f"Salida HTML: {html}")

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
    excluded_dirs = user_config.get("except", [])
    html = user_config.get("output_html", "true").strip().lower() in ["true", "1", "yes", "y", "on"]

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
    write_dataconfig (logging,config_path,component_mapping_path,base_path,components_to_search,output_file,log_file,from_version_str,to_version_str,html)


    # Validar las versiones desde y hasta
    try:
        from_version = Version(from_version_str) if from_version_str else None
        to_version = Version(to_version_str) if to_version_str else None
    except InvalidVersion as e:
        logging.error(f"Formato de versión inválido en la configuración: {e}")
        logging.error("Por favor, revise y corrija las versiones en el archivo de configuración.")
        exit(1)

    # Cargar la configuración de mapeo de componentes y la configuración de clientes
    component_mapping = load_json_file(component_mapping_path)
    customers_config = load_json_file(customers_config_path)

    # Verificar si el parámetro customer está presente y es válido
    if customer and customer in customers_config:
        logging.info(f"Cliente '{customer}' encontrado. Sobrescribiendo componentes a buscar.")
        components_to_search = customers_config[customer]
        logging.info(f"Componentes para el cliente '{customer}': {', '.join(customers_config[customer])}")
    else:
        logging.info(f"Cliente '{customer}' no encontrado o no proporcionado. Usando componentes de la configuración.")

    if components_to_search == "all" or "all" in components_to_search:
        logging.info("Componentes a buscar establecidos en 'all'. Usando todos los componentes del mapeo de componentes.")
        components_to_search = list(component_mapping.keys()) 

    components = find_latest_versions(base_path, component_mapping, components_to_search, from_version, to_version, excluded_dirs)
    
    if html : 
        generate_report_html(components, output_file)
    else :
        generate_report(components, output_file)
   

    end_time = datetime.now()
    logging.info(f"Hora de finalización: {end_time}")
    logging.info(f"Duración total de la ejecución: {end_time - start_time}")
    logging.info("Fin de la ejecución del script")