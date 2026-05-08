#!/usr/bin/env python3
"""
Image compressor for OpenClaw device channels (PocketClaw/Clawket)

Problem: WebSocket maxPayload is 1MB, so base64-encoded images must be < 1MB.
Solution: Compress images to target size before sending.

Usage:
    python3 image_compressor.py /path/to/image.jpg
    python3 image_compressor.py /path/to/image.jpg --target 800
    python3 image_compressor.py /path/to/image.jpg --output /path/to/output.jpg
"""

import sys
import os
import argparse
from pathlib import Path

def get_image_size_mb(filepath):
    """Get file size in MB"""
    return os.path.getsize(filepath) / (1024 * 1024)

def compress_image(input_path, output_path=None, target_kb=800, max_dimension=1600):
    """
    Compress image to target file size.
    
    Args:
        input_path: Path to input image
        output_path: Path for output (defaults to input_path.compressed.jpg)
        target_kb: Target file size in KB (default 800KB = safe under 1MB base64)
        max_dimension: Maximum width/height in pixels
    
    Returns:
        Path to compressed image
    """
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow not installed. Installing...")
        os.system(f"{sys.executable} -m pip install Pillow -q")
        from PIL import Image
    
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    # Default output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}.compressed.jpg"
    else:
        output_path = Path(output_path)
    
    # Open image
    img = Image.open(input_path)
    
    # Convert to RGB if necessary (handles PNG with transparency, etc.)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    original_size = get_image_size_mb(input_path)
    print(f"Original: {input_path.name}")
    print(f"  Size: {original_size:.2f} MB")
    print(f"  Dimensions: {img.size[0]}x{img.size[1]}")
    
    # If already small enough, just copy
    target_bytes = target_kb * 1024
    if original_size * 1024 * 1024 < target_bytes:
        print(f"  Already under {target_kb}KB, no compression needed.")
        if str(input_path) != str(output_path):
            import shutil
            shutil.copy2(input_path, output_path)
        return output_path
    
    # Resize if dimensions are too large
    width, height = img.size
    if width > max_dimension or height > max_dimension:
        ratio = min(max_dimension / width, max_dimension / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        print(f"  Resized to: {new_width}x{new_height}")
    
    # Progressive quality reduction until target size is met
    quality = 95
    min_quality = 30
    
    while quality >= min_quality:
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        compressed_size = os.path.getsize(output_path)
        
        if compressed_size <= target_bytes:
            print(f"  Compressed: {compressed_size / 1024:.1f} KB (quality={quality})")
            print(f"  Saved to: {output_path}")
            return output_path
        
        quality -= 5
    
    # If still too large, reduce dimensions further
    print(f"  Quality reduction not enough, reducing dimensions...")
    while compressed_size > target_bytes and (width > 100 or height > 100):
        width = int(width * 0.8)
        height = int(height * 0.8)
        img_resized = img.resize((width, height), Image.LANCZOS)
        img_resized.save(output_path, 'JPEG', quality=85, optimize=True)
        compressed_size = os.path.getsize(output_path)
        print(f"  Resized to {width}x{height}: {compressed_size / 1024:.1f} KB")
    
    print(f"  Final: {compressed_size / 1024:.1f} KB")
    print(f"  Saved to: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='Compress images for OpenClaw device channels',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 image_compressor.py photo.jpg
  python3 image_compressor.py photo.png --target 600
  python3 image_compressor.py photo.jpg --output small.jpg --max-width 1200
        """
    )
    parser.add_argument('input', help='Input image file')
    parser.add_argument('-o', '--output', help='Output file path (default: input.compressed.jpg)')
    parser.add_argument('-t', '--target', type=int, default=800, 
                        help='Target file size in KB (default: 800)')
    parser.add_argument('-m', '--max-dimension', type=int, default=1600,
                        help='Maximum width/height in pixels (default: 1600)')
    
    args = parser.parse_args()
    
    compress_image(
        input_path=args.input,
        output_path=args.output,
        target_kb=args.target,
        max_dimension=args.max_dimension
    )

if __name__ == '__main__':
    main()
