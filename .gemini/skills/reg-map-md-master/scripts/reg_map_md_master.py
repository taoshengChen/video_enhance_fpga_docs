import re
import sys
import os

def parse_bits(bits_str):
    """解析位域字符串，如 '15: 8' 或 '7'"""
    bits_str = str(bits_str).replace(" ", "").strip()
    if ":" in bits_str:
        parts = bits_str.split(":")
        high, low = int(parts[0]), int(parts[1])
        return list(range(low, high + 1))
    else:
        return [int(bits_str)]

def format_bits(bit_list):
    """将比特列表转换回字符串，如 [8,9,10] -> '10: 8'"""
    if len(bit_list) > 1:
        return f"{max(bit_list)}: {min(bit_list)}"
    return str(bit_list[0])

def parse_reset(reset_str):
    """将复位值转换为整数"""
    reset_str = str(reset_str).strip().lower().replace("_", "")
    if reset_str == "-" or not reset_str:
        return 0
    try:
        if reset_str.startswith("0x"):
            return int(reset_str, 16)
        return int(reset_str)
    except ValueError:
        return 0

class Register:
    def __init__(self, name, id_str, addr, rtype, section_id, subsection_content, original_desc=""):
        self.name = name # Display name from title
        self.id_str = id_str # ID from title after '—'
        self.addr = addr
        self.rtype = rtype
        self.section_id = section_id # e.g. 6.2.1
        self.subsection_content = subsection_content
        self.original_desc = original_desc # From summary table
        self.fields = [] # List of dicts: {name, bits, reset, desc}

    def calculate_default(self):
        default_val = 0
        used_bits = set()
        for f in self.fields:
            bits = parse_bits(f['bits'])
            # Check overlap
            for b in bits:
                if b in used_bits:
                    raise RuntimeError(f"Error: Bit overlap detected in register {self.name} ({self.id_str}) at bit {b}")
                used_bits.add(b)
            reset = parse_reset(f['reset'])
            # Check overflow
            max_val = (1 << len(bits)) - 1
            if reset > max_val:
                print(f"Warning: Reset value {hex(reset)} overflow for field {f['name']} (width {len(bits)}) in {self.id_str}")
            default_val |= (reset << min(bits))
        return f"0x{default_val:04X}"

    def pad_reserved(self):
        """补全 0-15 比特中的空隙"""
        defined_bits = set()
        for f in self.fields:
            defined_bits.update(parse_bits(f['bits']))
        
        missing_bits = set(range(16)) - defined_bits
        if not missing_bits:
            return

        sorted_missing = sorted(list(missing_bits))
        gaps = []
        if sorted_missing:
            current_gap = [sorted_missing[0]]
            for i in range(1, len(sorted_missing)):
                if sorted_missing[i] == sorted_missing[i-1] + 1:
                    current_gap.append(sorted_missing[i])
                else:
                    gaps.append(current_gap)
                    current_gap = [sorted_missing[i]]
            gaps.append(current_gap)

        for gap in gaps:
            gap_str = format_bits(gap)
            exists = False
            for f in self.fields:
                if f['bits'] == gap_str and '保留' in f['name']:
                    exists = True
                    break
            if not exists:
                self.fields.append({
                    'name': '保留',
                    'bits': gap_str,
                    'reset': '0x0',
                    'desc': '保留'
                })
        self.fields.sort(key=lambda x: min(parse_bits(x['bits'])), reverse=True)

def generate_table(headers, rows):
    """生成紧凑的 Markdown 表格"""
    if not rows:
        return ""
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join([":---"] * len(headers)) + " |")
    for row in rows:
        processed_row = [str(val).replace('\n', '<br/>') for val in row]
        lines.append("| " + " | ".join(processed_row) + " |")
    return "\n".join(lines)

def process_file(file_path):
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    summary_map = {}
    summary_match = re.search(r'## 6.1 寄存器摘要.*?<small><b>表 6.1 寄存器摘要</b></small>\n\n(.*?)(?=\n## |$|> \[!|\Z)', content, re.DOTALL)
    if summary_match:
        table_content = summary_match.group(1).strip()
        lines = table_content.split('\n')
        if len(lines) > 2:
            for line in lines[2:]:
                parts = [p.strip() for p in line.strip('|').split('|')]
                if len(parts) >= 6:
                    summary_map[parts[0]] = parts[4]

    section62_pattern = r'(## 6.2 寄存器描述.*?)(\n## |$)'
    section62_match = re.search(section62_pattern, content, re.DOTALL)
    if not section62_match:
        print("Error: Could not find section 6.2 寄存器描述")
        return

    section62_full = section62_match.group(1)
    title_matches = list(re.finditer(r'\n### 6.2\.\d+ (.*?)—(.*?)\n', section62_full))
    
    registers = []
    for i, match in enumerate(title_matches):
        name = match.group(1).strip()
        reg_id = match.group(2).strip()
        start_pos = match.start()
        end_pos = title_matches[i+1].start() if i+1 < len(title_matches) else len(section62_full)
        subsection_raw = section62_full[start_pos:end_pos]
        
        addr_m = re.search(r'\*\*寄存器地址：(.*?)\*\*', subsection_raw)
        addr = addr_m.group(1).strip() if addr_m else "0x00"
        rtype_m = re.search(r'\*\*读写类型：(.*?)\*\*', subsection_raw)
        rtype = rtype_m.group(1).strip() if rtype_m else "RW"
        
        reg = Register(name, reg_id, addr, rtype, f"6.2.{i+1}", subsection_raw, summary_map.get(name, name))
        field_table_match = re.search(r'\|.*?\n\|.*?\n((?:\|.*?\n)+)', subsection_raw)
        if field_table_match:
            rows = field_table_match.group(1).strip().split('\n')
            for row in rows:
                parts = [p.strip() for p in row.strip('|').split('|')]
                if len(parts) >= 4:
                    if parts[0] == "位域名称": continue
                    reg.fields.append({'name': parts[0], 'bits': parts[1], 'reset': parts[2], 'desc': parts[3]})
        registers.append(reg)

    if not registers:
        print("No registers found in 6.2.")
        return

    for i, reg in enumerate(registers):
        reg.addr = f"0x{i:02x}"
        reg.section_id = f"6.2.{i+1}"
        reg.pad_reserved()
        new_subsection = f"\n### {reg.section_id} {reg.name}—{reg.id_str}\n\n"
        new_subsection += f"**寄存器地址：{reg.addr}**\n\n"
        new_subsection += f"**读写类型：{reg.rtype}**\n\n"
        new_subsection += f"<small><b>表 6.{i+2} {reg.id_str}</b></small>\n\n"
        field_headers = ["位域名称", "位域", "复位值", "描述"]
        field_rows = [[f['name'], f['bits'], f['reset'], f['desc']] for f in reg.fields]
        new_subsection += generate_table(field_headers, field_rows)
        new_subsection += "\n"
        reg.subsection_content = new_subsection

    summary_headers = ["名称", "地址", "读写类型", "默认值", "描述", "章节"]
    summary_rows = []
    for reg in registers:
        default_val = reg.calculate_default()
        anchor_id = f"{reg.section_id} {reg.name}—{reg.id_str}"
        link = f"[{reg.section_id}小节](###{anchor_id})"
        summary_rows.append([reg.name, reg.addr, reg.rtype, default_val, reg.original_desc, link])
    
    new_summary_table = generate_table(summary_headers, summary_rows)

    if summary_match:
        content = content[:summary_match.start(1)] + new_summary_table + "\n" + content[summary_match.end(1):]
    
    section62_match = re.search(section62_pattern, content, re.DOTALL)
    new_62_content = "## 6.2 寄存器描述\n" + "".join(reg.subsection_content for reg in registers)
    content = content[:section62_match.start(1)] + new_62_content + content[section62_match.end(1):]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Update completed. Total {len(registers)} registers processed.")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        process_file(sys.argv[1])
