#!/usr/bin/env python3
"""
size_report.py - Generate markdown size report from ESP-IDF size output

Usage:
    idf.py size > size_output.txt
    python3 scripts/size_report.py size_output.txt [output.md]
"""

import sys
import re
import sys

def parse_size_output(content: str) -> dict:
    """Parse ESP-IDF size output into structured data"""
    data = {
        'components': [],
        'total_flash': 0,
        'total_ram': 0,
        'flash_total': 0,
        'ram_total': 0
    }
    
    # Parse component table
    # Format: component_name   flash   ram
    lines = content.strip().split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect table header
        if 'component' in line.lower() and ('flash' in line.lower() or 'ram' in line.lower()):
            in_table = True
            continue
            
        if in_table and not line.startswith('='):
            # Parse component line
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                name = parts[0]
                try:
                    flash = int(parts[1].replace(',', ''))
                    ram = int(parts[2].replace(',', ''))
                    data['components'].append({
                        'name': name,
                        'flash': flash,
                        'ram': ram
                    })
                    data['total_flash'] += flash
                    data['total_ram'] += ram
                except ValueError:
                    pass
                    
        # Total line
        if 'Total' in line and ('flash' in line.lower() or 'ram' in line.lower()):
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                try:
                    data['flash_total'] = int(parts[1].replace(',', ''))
                    data['ram_total'] = int(parts[2].replace(',', ''))
                except ValueError:
                    pass
                    
        # Appended files (firmware image)
        if 'appended' in line.lower() or 'ota' in line.lower():
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                try:
                    size = int(parts[1].replace(',', ''))
                    data['flash_total'] = max(data['flash_total'], size)
                except ValueError:
                    pass
    
    return data

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def generate_report(data: dict) -> str:
    """Generate markdown report"""
    lines = []
    lines.append("# Firmware Size Report")
    lines.append("")
    lines.append(f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Summary
    flash_total = data['flash_total'] if data['flash_total'] else data['total_flash']
    ram_total = data['ram_total'] if data['ram_total'] else data['total_ram']
    
    lines.append("## Summary")
    lines.append(f"- **Flash Usage**: {format_bytes(data['total_flash'])} / {format_bytes(8*1024*1024)} ({data['total_flash']/8192000*100:.1f}% of 8MB)")
    lines.append(f"- **RAM Usage**: {format_bytes(data['total_ram'])} / {format_bytes(320*1024)} ({data['total_ram']/327680*100:.1f}% of 320KB)")
    lines.append(f"- **Flash Total (with bootloader)**: {format_bytes(data['flash_total'] if data['flash_total'] else data['total_flash'])}")
    lines.append(f"- **RAM Total**: {format_bytes(data['ram_total'] if data['ram_total'] else data['total_ram'])}")
    lines.append("")
    
    # Component breakdown
    lines.append("## Component Breakdown")
    lines.append("| Component | Flash | RAM | % Flash | % RAM |")
    lines.append("|-----------|-------|-----|---------|-------|")
    
    flash_total = data['total_flash']
    ram_total = data['total_ram']
    
    # Sort by flash usage
    sorted_components = sorted(data['components'], key=lambda x: x['flash'], reverse=True)
    
    for comp in sorted_components:
        flash_pct = (comp['flash'] / flash_total * 100) if flash_total > 0 else 0
        ram_pct = (comp['ram'] / ram_total * 100) if ram_total > 0 else 0
        lines.append(f"| {comp['name']} | {format_bytes(comp['flash'])} | {format_bytes(comp['ram'])} | {flash_pct:.1f}% | {ram_pct:.1f}% |")
    
    lines.append("")
    
    # Flash usage breakdown
    lines.append("## Flash Usage Details")
    lines.append("| Region | Size | Percentage |")
    lines.append("|--------|------|------------|")
    
    if data['flash_total']:
        flash_total = data['flash_total']
        lines.append(f"| Application | {format_bytes(data['total_flash'])} | {data['total_flash']/flash_total*100:.1f}% |")
        lines.append(f"| Bootloader + Partition Table | {format_bytes(flash_total - data['total_flash'])} | {(flash_total - data['total_flash'])/flash_total*100:.1f}% |")
        lines.append(f"| **Total** | **{format_bytes(flash_total)}** | **100%** |")
    else:
        lines.append(f"| Application | {format_bytes(data['total_flash'])} | N/A |")
    
    lines.append("")
    
    # RAM breakdown
    lines.append("## RAM Usage Details")
    lines.append("| Region | Size | Percentage |")
    lines.append("|--------|------|------------|")
    if ram_total > 0:
        # Estimate breakdown
        iram = sum(c['ram'] for c in data['components'] if 'esp' in c['name'].lower() or 'freertos' in c['name'].lower() or 'heap' in c['name'].lower())
        dram = data['total_ram'] - iram
        lines.append(f"| IRAM (Code) | {format_bytes(iram)} | {iram/ram_total*100:.1f}% |")
        lines.append(f"| DRAM (Data) | {format_bytes(dram)} | {dram/ram_total*100:.1f}% |")
        lines.append(f"| **Total** | **{format_bytes(ram_total)}** | **100%** |")
    
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated by size_report.py*")
    
    return '\n'.join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 size_report.py <size_output_file> [output.md]")
        print("  Example:")
        print("    idf.py size > size_output.txt")
        print("    python3 size_report.py size_output.txt size_report.md")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "size_report.md"
    
    with open(input_file, 'r') as f:
        content = f.read()
    
    data = parse_size_output(content)
    report = generate_report(data)
    
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"Report written to {output_file}")

if __name__ == '__main__':
    main()