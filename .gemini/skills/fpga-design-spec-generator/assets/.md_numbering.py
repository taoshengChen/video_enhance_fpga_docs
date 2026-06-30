import re
import os
import argparse

class MarkdownNumbering:
    def __init__(self, sep='.'):
        self.sep = sep
        self.section_counters = [0] * 6
        self.figure_counter = 0
        self.table_counter = 0
        self.in_code_block = False
        self.in_math_block = False

    def process_file(self, filepath):
        output = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = self._process_line(line)
                output.append(line)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(output)

    def _process_line(self, line):
        stripped = line.strip()
        
        # 检测代码块边界
        if re.match(r'^`{3,}', stripped):
            self.in_code_block = not self.in_code_block
            return line
        
        # 检测公式块边界
        math_delim = stripped.count('$$')
        if math_delim > 0:
            self.in_math_block = not self.in_math_block
        
        # 跳过代码/公式块内容
        if self.in_code_block or self.in_math_block:
            return line
        
        # 标题处理逻辑
        match = re.match(r'^(#+)\s*(\d+\.?)*\s+(.*)', line)
        if match:
            hashes, _, content = match.groups()
            level = len(hashes)
            self._update_section_counters(level)
            number = '.'.join(str(x) for x in self.section_counters[:level] if x > 0)
            return f"{hashes} {number}{self.sep} {content}
"

        # 图题注处理逻辑
        match = re.match(r'^<small><b>图\s*(\d+\.?)*\s*(.*)</b></small>\s*$', line)
        if match:
            _, content = match.groups()
            self._update_figure_counter()
            number = str(self.section_counters[0]) + '.' + str(self.figure_counter)
            return f"<small><b>图{number}{self.sep} {content}</b></small>
"

        # 表格题注处理逻辑
        match = re.match(r'^<small><b>表\s*(\d+\.?)*\s*(.*)</b></small>\s*$', line)
        if match:
            _, content = match.groups()
            self._update_table_counter()
            number = str(self.section_counters[0]) + '.' + str(self.table_counter)
            return f"<small><b>表 {number}{self.sep} {content}</b></small>
"
        
        return line

    def _update_section_counters(self, level):
        if level == 1:
            self.figure_counter = 0
            self.table_counter = 0
        self.section_counters[level-1] += 1
        self.section_counters[level:] = [0]*(6-level)

    def _update_figure_counter(self):
        self.figure_counter += 1

    def _update_table_counter(self):
        self.table_counter += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="要处理的Markdown文件")
    parser.add_argument("--sep", default="", help="编号分隔符，默认为点")
    parser.add_argument("--start", type=int, default=1,
                        help="起始编号层级（1-6）")
    
    args = parser.parse_args()
    
    processor = MarkdownNumbering(sep=args.sep)
    for f in args.files:
        if f.endswith('.md'):
            processor.process_file(f)
