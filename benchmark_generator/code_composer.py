import os
import uuid

def load_benchmark_code(benchmark_name, language="python"):
    current_dir = os.getcwd()
    path_to_code = os.path.join(current_dir, benchmark_name, language, "function.py" if language == "python" else "function.js")
    if os.path.exists(path_to_code):
        with open(path_to_code, "r") as source_file:
            source_code = source_file.read()
            [_, after_test] = source_code.split("#test")
            [_, after_import] = after_test.split("#import")
            [import_part, after_function] = after_import.split("#function")
            [function_part, run_part] = after_function.split("#run")
            return {
                "import": import_part,
                "function": function_part,
                "run": run_part
            }
    else:
        print("Path: " + path_to_code + " not exist")
    return {
                "import": "",
                "function": "",
                "run": ""
            }

def intend(body):
    new_body = ""
    for line in body.splitlines():
        new_body += "\n\t" + line
    return new_body

def generate_huge_dict(number_of_elements):
    return {
        str(uuid.uuid1()) + "-" + str(i): str(uuid.uuid1()) for i in range(number_of_elements)      # uuid has more predictible size than plain numbers
    }

def generate_python_handler(config, code_maps):
    code = "\ndef handler(event):\n"
    #add invoke of benchmarks
    handler_function = "result = {}\n"
    for (number, (benchmark_name, benchmark_config)) in enumerate(config):
        handler_function += "\nnumber = " + str(number) + "\n"
        handler_function += "config = " + str(benchmark_config) + "\n"
        handler_function += code_maps[benchmark_name]["run"]

    if benchmark_name == "artificial_code":
        number_of_elements = benchmark_config.get("number_of_elements", 0)
        handler_function += "artificial_dict" + str(number) + " = " + str(generate_huge_dict(number_of_elements))

    handler_function += """\nreturn {'result': result }"""     # dummy result, different doesn't work

    code += intend(handler_function)

    return code


def generate_async_nodejs_handler(config, code_maps):
    code = "\nexports.handler = async function(event) {\n"
    #add invoke of benchmarks
    handler_function = """var result = {};\nawait (async () => { return [result, 0] })()"""
    for (number, (benchmark_name, benchmark_config)) in enumerate(config):
        handler_function += ".then(async ([result, number]) => {\n"
        inner_function = "var config = " + str(benchmark_config) + ";\n"
        inner_function += code_maps[benchmark_name]["run"] + "\n"
        inner_function += "return [result, number + 1]\n"
        handler_function += intend(inner_function)
        handler_function += "\n})\n"


    if benchmark_name == "artificial_code":
        number_of_elements = benchmark_config.get("number_of_elements", 0)
        handler_function += "var artificial_dict" + str(number) + " = " + str(generate_huge_dict(number_of_elements)) + ";"

    handler_function += """\nreturn {'result': result }\n}"""

    code += intend(handler_function)

    return code

def compose(config, language):

    code = ""

    benchmarks_list = {benchmark for (benchmark, benchmark_config) in config}

    # load code of benchmarks
    code_maps = {
        benchmark_name: load_benchmark_code(benchmark_name, language) for benchmark_name in benchmarks_list
    }

    # add imports
    for code_map in code_maps.values():
        code += code_map["import"] + "\n"       # todo not so easy for nodejs- twice imports are not possible

    #add functions
    for code_map in code_maps.values():
        code += code_map["function"] + "\n"

    if language == "python":
        return code + generate_python_handler(config, code_maps)
    elif language == "async_nodejs":
        return code + generate_async_nodejs_handler(config, code_maps)
    else:
        return ""

    
