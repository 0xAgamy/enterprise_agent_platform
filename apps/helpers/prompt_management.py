import yaml
from jinja2 import Template

def prompt_template_config(yaml_file, prompt_key):
    with open(yaml_file,'r') as file:
        config= yaml.safe_load(file)
    template_content= config["prompts"][prompt_key]
    return Template(template_content)
