import re
from urllib.parse import urlparse

def convert_openapi_file(input_file, output_file, server_url):
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    added_servers = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Add servers section before paths
        if line.startswith('paths:') and not added_servers:
            new_lines.append('servers:\n')
            new_lines.append(f'  - url: {server_url}\n')
            new_lines.append('\n')
            added_servers = True
        
        # Convert full URL paths to relative paths
        url_match = re.match(r'^  (https?://[^:]+):', line)
        if url_match:
            full_url = url_match.group(1)
            parsed = urlparse(full_url)
            path_part = parsed.path
            query = parsed.query
            if query:
                safe_query = query.replace('&', '_').replace('=', '-')
                new_path = f"{path_part}_{safe_query}"
            else:
                new_path = path_part
            new_lines.append(f'  {new_path}:\n')
            i += 1
            continue
        
        # Remove 'produces' lines (OpenAPI 2.0 syntax)
        if re.match(r'^\s+produces:\s*$', line):
            i += 1
            # Skip the list items under produces
            while i < len(lines) and re.match(r'^\s+-\s', lines[i]):
                i += 1
            continue
        
        # Remove 'status' property (not valid in OpenAPI 3.x operations)
        if re.match(r'^\s+status:\s*\d+', line):
            i += 1
            continue
        
        # Remove 'allowEmptyValue' (deprecated in OpenAPI 3.1)
        if re.match(r'^\s+allowEmptyValue:\s*(true|false)', line):
            i += 1
            continue
        
        # Fix schema at wrong indentation level under content type
        # Pattern: "            application/json:\n            schema:" should be "            application/json:\n              schema:"
        schema_match = re.match(r'^(\s+)schema:\s*$', line)
        if schema_match and len(new_lines) >= 1:
            prev_line = new_lines[-1]
            content_type_match = re.match(r'^(\s+)(application/json|text/html):\s*$', prev_line)
            if content_type_match:
                content_indent = content_type_match.group(1)
                schema_indent = schema_match.group(1)
                # If schema is at same level as content type, fix indentation
                if len(schema_indent) <= len(content_indent):
                    # Add indented schema line
                    new_lines.append(f'{content_indent}  schema:\n')
                    i += 1
                    # Now indent all following lines that belong to this schema block
                    # until we hit a line at same or lesser indentation as schema
                    base_indent = len(schema_indent)
                    while i < len(lines):
                        next_line = lines[i]
                        next_match = re.match(r'^(\s*)\S', next_line)
                        if next_match:
                            next_indent = len(next_match.group(1))
                            # If we hit a line at or less than schema indent, stop
                            if next_indent <= base_indent:
                                break
                            # Otherwise, add 2 spaces to indent it properly
                            new_lines.append('  ' + next_line)
                            i += 1
                        else:
                            # Empty line or whitespace only
                            new_lines.append(next_line)
                            i += 1
                    continue
        
        # Fix enum at wrong indentation level
        enum_match = re.match(r'^(\s+)enum:\s*$', line)
        if enum_match and len(new_lines) >= 2:
            prev_line = new_lines[-1]
            prev_prev_line = new_lines[-2] if len(new_lines) >= 2 else ""
            
            type_match = re.match(r'^(\s+)type:\s*string\s*$', prev_line)
            schema_match = re.match(r'^(\s+)schema:\s*$', prev_prev_line)
            
            if type_match and schema_match:
                type_indent = type_match.group(1)
                enum_indent = enum_match.group(1)
                
                if len(enum_indent) < len(type_indent):
                    new_lines.append(f'{type_indent}enum:\n')
                    i += 1
                    continue
        
        new_lines.append(line)
        i += 1
    
    # Post-process: convert single-quoted status codes to double-quoted
    # '200': -> "200":
    content = ''.join(new_lines)
    content = content.replace("'200':", '"200":')
    content = content.replace("'201':", '"201":')
    content = content.replace("'400':", '"400":')
    content = content.replace("'401':", '"401":')
    content = content.replace("'403':", '"403":')
    content = content.replace("'404':", '"404":')
    content = content.replace("'500':", '"500":')
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Converted {input_file} -> {output_file}")

convert_openapi_file(
    'cronos-api-v2.yaml',
    'cronos-api-v2-fixed.yaml', 
    'https://explorer-api.cronos.org/testnet'
)
convert_openapi_file(
    'cronoszkevm-api.yaml',
    'cronoszkevm-api-fixed.yaml',
    'https://explorer-api.zkevm.cronos.org'
)
