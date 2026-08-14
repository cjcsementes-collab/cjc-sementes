with open("seed.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

excluded_skus = [
    "PRDT00089", "PRDT00088", "PRDT00087", "PRDT00086", 
    "PRDT00085", "PRDT00083", "PRDT00082", "PRDT00081", 
    "PRDT0070", "PRDT00051", "PRDT48", "PRDT00031"
]

new_lines = []
for line in lines:
    skip = False
    for sku in excluded_skus:
        if f'"codigo_bling": "{sku}"' in line:
            skip = True
            break
    if not skip:
        new_lines.append(line)

with open("seed.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("seed.py filtered!")
