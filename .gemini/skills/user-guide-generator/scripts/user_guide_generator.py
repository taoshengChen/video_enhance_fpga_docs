import re
import sys
import os

class UserGuideGenerator:
    def __init__(self, ds_path):
        with open(ds_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def clean_html_colors(self, text):
        """移除 HTML 标签中的颜色属性和 font color 标签"""
        # 移除 <font color="..."> 和 </font>
        text = re.sub(r'<font\s+color=[^>]+>(.*?)</font>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
        # 移除 style="color:..." 或 style='color:...'
        text = re.sub(r'style=(["\'])\s*color:[^;>]+;?\s*\1', '', text, flags=re.IGNORECASE)
        # 移除剩余的 font 标签但保留内容
        text = re.sub(r'<font[^>]*>(.*?)</font>', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
        return text

    def extract_chapter(self, chapter_title_pattern):
        """提取指定标题的章节内容，并剔除资源相关的子章节"""
        lines = self.content.split('\n')
        start_line = -1
        header_level = -1
        
        # 匹配标题
        pattern = re.compile(rf'^#+\s+{chapter_title_pattern}', re.IGNORECASE)
        
        for i, line in enumerate(lines):
            if pattern.match(line):
                start_line = i
                header_level = len(re.match(r'^(#+)', line).group(1))
                break
        
        if start_line == -1:
            return ""

        extracted_lines = []
        skip_mode = False
        skip_level = -1
        
        # 定义需要剔除的子章节关键词
        exclude_keywords = [
            "资源预估", "资源统计", "资源评估", "硬件资源",
            "Resource Estimation", "Resource Statistics", "Resource Evaluation",
            "饼图", "Pie Chart", "deployment statistics"
        ]

        # 重构后的提取循环，支持子章节跳过
        for i in range(start_line, len(lines)):
            line = lines[i].strip()
            match = re.match(r'^(#+)', line)
            
            if i > start_line and match:
                current_level = len(match.group(1))
                # 如果遇到同级或更高级标题（例如在提取 6.2 时遇到了 6.3 或 7），停止提取
                if current_level <= header_level:
                    break
                
                # 如果当前正在跳过模式中，检查是否遇到了更高或同级的标题以退出跳过模式
                if skip_mode and current_level <= skip_level:
                    skip_mode = False
                
                # 检查标题是否命中剔除关键词
                if any(kw in line for kw in exclude_keywords):
                    skip_mode = True
                    skip_level = current_level
                    continue
            
            # 额外检查：如果行内包含明显的资源统计表格特征且不在跳过模式，也尝试过滤（可选，目前主要靠标题）
            if not skip_mode:
                # 过滤修订记录中的资源描述
                if chapter_title_pattern == "2 修订记录" or "修订记录" in chapter_title_pattern:
                    line = re.sub(r'(\d+\.\s+)?(更新|增加|移除)资源(评估|统计|预估).*?(<br />|\n|$)', '', line, flags=re.IGNORECASE)
                
                extracted_lines.append(lines[i]) # 使用原始行保留缩进
        
        content = '\n'.join(extracted_lines)
        return self.clean_html_colors(content)

    def wrap_with_page_break(self, content):
        """在章节末尾添加分页符"""
        if not content.strip():
            return ""
        return content.strip() + '\n\n<div STYLE="page-break-after: always;"></div>\n\n'

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 user_guide_generator.py <ds_path> <chapter_pattern>")
        sys.exit(1)

    ds_path = sys.argv[1]
    chapter_pattern = sys.argv[2]
    
    if not os.path.exists(ds_path):
        print(f"Error: File '{ds_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    generator = UserGuideGenerator(ds_path)
    result = generator.extract_chapter(chapter_pattern)
    
    if result:
        # 脚本模式下直接打印结果，方便 LLM 捕获并组装
        print(generator.wrap_with_page_break(result))
    else:
        print(f"Chapter '{chapter_pattern}' not found.", file=sys.stderr)

if __name__ == "__main__":
    main()
