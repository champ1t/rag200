
content = """
 var addy99195 = 's&#111;mb&#111;&#111;nc' + '&#64;';
 addy99195 = addy99195 + 'COMPANY_NAME' + '&#46;' + 'c&#111;' + '&#46;' + 'th';
"""

def parse(text):
    lines = text.split('\n')
    var_name = None
    parts = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Init: var addy... = ...
        if line.startswith("var addy"):
            # var addy99195 = '...
            tokens = line.split("=")
            var_name = tokens[0].replace("var ", "").strip()
            rhs = tokens[1].strip().rstrip(";")
            print(f"Init {var_name} = {rhs}")
            parts.append(rhs)
            
        # Add: addy... = addy... + ...
        elif var_name and line.startswith(var_name):
             # addy99195 = addy99195 + ...
             tokens = line.split("=")
             rhs = tokens[1].strip().rstrip(";")
             # Remove LHS repeat
             # addy99195 + '...'
             if rhs.startswith(var_name):
                 rhs = rhs.replace(var_name, "", 1).strip()
                 # trim leading +
                 if rhs.startswith("+"):
                     rhs = rhs[1:].strip()
                 print(f"Add {rhs}")
                 parts.append(rhs)

parse(content)
