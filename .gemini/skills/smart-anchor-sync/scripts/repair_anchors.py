import re
import sys
import difflib

def get_anchor_id(text):
    """
    根据标题文本生成可能的锚点 ID。
    这里采用简单清理模式，保留中文字符和基础标点，去除前缀空格。
    """
    return text.strip()

def strip_numbers(text):
    """
    剥离标题开头的数字序号（如 1.2.3, 第1章, 3.4等）
    """
    # 匹配形如 1.2.3 或 1. 或 第1章 或 3.4.12
    return re.sub(r'^([\d\.]+|第\s*\d+\s*[章节])\s*', '', text.strip())

def repair_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    content = "".join(lines)
    
    # 1. 提取所有标题及其所在的行
    # 匹配 # 标题, ## 标题, ### 标题 等
    headers = []
    header_pattern = re.compile(r'^(#+)\s+(.+)$', re.MULTILINE)
    for match in header_pattern.finditer(content):
        level_hashes = match.group(1)
        header_text = match.group(2).strip()
        headers.append({
            'full_text': header_text,
            'clean_text': strip_numbers(header_text),
            'level': len(level_hashes)
        })

    # 创建当前有效的标题池（用于直接查找）
    valid_headers_set = {h['full_text'] for h in headers}
    clean_to_full = {h['clean_text']: h['full_text'] for h in headers}

    # 2. 匹配并分析链接
    # 匹配 [text](###anchor) 或 [text](#anchor)
    # 注意：用户提供的文档中出现了 (###6.2.12 ...) 这种非标准但特定的写法
    link_pattern = re.compile(r'\[([^\]]+)\]\((#+)([^#\)]+)\)')
    
    replacements = []

    def replace_func(match):
        full_match = match.group(0)
        link_text = match.group(1).strip()
        hashes = match.group(2)
        anchor = match.group(3).strip()

        clean_anchor = strip_numbers(anchor)
        clean_link_text = strip_numbers(link_text)
        
        target_header = None
        
        # 如果锚点在标题池中（可能是旧的也可能是修复过的）
        if anchor in valid_headers_set:
            # 即使 ID 有效，也要检查文本是否需要同步
            if clean_link_text != clean_anchor and clean_link_text in [h['clean_text'] for h in headers]:
                # 这种情况下，link_text 可能是一个旧的序号文本，我们需要把它对齐到当前的 anchor
                print(f"  [对齐] 同步链接文本: '{link_text}' -> '{anchor}'")
                return f"[{anchor}]({hashes}{anchor})"
            
            # 检查格式：确保括号内没有空格 (例如 [text](##title) 而不是 [text](## title))
            reconstructed = f"[{link_text}]({hashes}{anchor})"
            if reconstructed != full_match:
                print(f"  [格式] 移除锚点空格: '{full_match}' -> '{reconstructed}'")
                return reconstructed

            return full_match

        # 尝试剥离序号后的语义匹配
        # ... (后续逻辑不变)
        
        # 策略A：完全语义一致（仅序号变动）
        if clean_anchor in clean_to_full:
            target_header = clean_to_full[clean_anchor]
            print(f"  [修复] 基于语义一致性: '{anchor}' -> '{target_header}'")
        
        # 策略B：模糊语义匹配（编辑距离）
        else:
            possible_matches = difflib.get_close_matches(clean_anchor, clean_to_full.keys(), n=1, cutoff=0.6)
            if possible_matches:
                matched_clean = possible_matches[0]
                target_header = clean_to_full[matched_clean]
                print(f"  [修复] 基于模糊匹配: '{anchor}' -> '{target_header}'")

        if target_header:
            # 关键改进：如果链接文本的语义与旧锚点一致，或者链接文本本身就是旧锚点，则同步更新链接文本
            if clean_link_text == clean_anchor:
                return f"[{target_header}]({hashes}{target_header})"
            else:
                # 如果链接文本是自定义的（如 [点击这里](#旧标题)），则只更新锚点
                return f"[{link_text}]({hashes}{target_header})"

        # 如果无法匹配，保持原样
        print(f"  [警告] 无法找到匹配项: '{anchor}'")
        return match.group(0)

    new_content = link_pattern.sub(replace_func, content)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\n文件 {file_path} 修复完成。")
    else:
        print(f"\n未发现需要修复的失效链接。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 repair_anchors.py <md_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    print(f"正在扫描并修复: {file_path} ...")
    repair_markdown(file_path)
