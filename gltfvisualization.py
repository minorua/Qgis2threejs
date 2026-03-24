#!/usr/bin/env python3
"""
GLTF Tile Visualization Script
===============================

This script reads .gltf files from a folder and plots the tile centers
in a matplotlib graph to visualize the tile distribution.

Usage:
    python3 gltfvisualization.py

Example:
    python3 gltfvisualization.py
"""

import os
import json
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import numpy as np

# Try to import rasterio for TIFF support
try:
    import rasterio
    from rasterio.plot import show
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    print("Warning: rasterio not available. Install with: pip install rasterio")

def extract_tile_centers_from_gltf(file_path):
    """
    Extract tile center coordinates from a .gltf file.
    
    Args:
        file_path (str): Path to the GLTF file
        
    Returns:
        tuple: (center_x, center_y, tile_width, tile_height) or None if error
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        print(f"\n=== Analyzing GLTF file: {os.path.basename(file_path)} ===")
        print(f"File structure: {list(data.keys())}")
        
        # Method 1: Check scene extras
        if 'scenes' in data and len(data['scenes']) > 0:
            scene = data['scenes'][0]
            print(f"Scene 0: {scene}")
            if 'extras' in scene:
                extras = scene['extras']
                print(f"Scene extras: {extras}")
                if 'center_x' in extras and 'center_y' in extras:
                    center_x = float(extras['center_x'])
                    center_y = float(extras['center_y'])
                    tile_width = float(extras.get('tile_width', 150))
                    tile_height = float(extras.get('tile_height', 150))
                    print(f"✓ Found in scene extras: ({center_x}, {center_y}), size: {tile_width}x{tile_height}")
                    return center_x, center_y, tile_width, tile_height
        
        # Method 2: Check node translation and scale
        if 'nodes' in data and len(data['nodes']) > 0:
            print(f"Found {len(data['nodes'])} nodes")
            for i, node in enumerate(data['nodes']):
                print(f"Node {i}: {node}")
                if 'translation' in node and len(node['translation']) >= 2:
                    center_x = float(node['translation'][0])
                    center_y = float(node['translation'][2])  # GLTF uses Y-up, so Z is our Y
                    scale = node.get('scale', [1, 1, 1])
                    tile_width = float(scale[0]) * 150
                    tile_height = float(scale[2]) * 150
                    print(f"✓ Found in node {i} translation: ({center_x}, {center_y}), scale: {scale}")
                    return center_x, center_y, tile_width, tile_height
        
        # Method 3: Check asset extras
        if 'asset' in data and 'extras' in data['asset']:
            extras = data['asset']['extras']
            print(f"Asset extras: {extras}")
            if 'center_x' in extras and 'center_y' in extras:
                center_x = float(extras['center_x'])
                center_y = float(extras['center_y'])
                tile_width = float(extras.get('tile_width', 150))
                tile_height = float(extras.get('tile_height', 150))
                print(f"✓ Found in asset extras: ({center_x}, {center_y}), size: {tile_width}x{tile_height}")
                return center_x, center_y, tile_width, tile_height
        
        # Method 4: Check for any other coordinate information
        print("Searching for coordinate information in other fields...")
        for key, value in data.items():
            if isinstance(value, dict) and ('x' in str(value).lower() or 'y' in str(value).lower() or 'coord' in str(value).lower()):
                print(f"Potential coordinate field '{key}': {value}")
        
        # Method 5: Parse filename and convert to background coordinate system
        filename = os.path.basename(file_path)
        try:
            parts = filename.replace('.gltf', '').split('_')
            if len(parts) >= 3 and parts[0] == 'tile':
                row = int(parts[1])
                col = int(parts[2])
                
                # Use the same coordinate system as your settings files (background)
                # From your previous analysis: X(1617.0 to 8817.0), Y(29228.0 to 33128.0)
                background_min_x = 1617.0
                background_max_x = 8817.0
                background_min_y = 29228.0
                background_max_y = 33128.0
                
                # Use the EXACT same coordinate system as your settings files
                # From your previous analysis: 300x300 tiles with specific spacing
                tile_width = 300.0  # Your tiles are 300x300 units
                tile_height = 300.0
                
                # Calculate center coordinates using the same logic as your settings files
                # Start from the base coordinates and add tile offsets
                center_x = background_min_x + (col * tile_width) + (tile_width / 2)
                center_y = background_min_y + (row * tile_height) + (tile_height / 2)
                
                # Ensure coordinates are within background bounds
                center_x = max(background_min_x, min(background_max_x, center_x))
                center_y = max(background_min_y, min(background_max_y, center_y))
                
                print(f"✓ {filename}: row={row}, col={col} -> background coords: ({center_x:.2f}, {center_y:.2f})")
                print(f"  Base: ({background_min_x}, {background_min_y}), Tile size: {tile_width}x{tile_height}")
                return center_x, center_y, tile_width, tile_height
        except (ValueError, IndexError) as e:
            print(f"Error parsing filename {filename}: {e}")
            pass
        
        print(f"✗ No coordinate information found in {file_path}")
        return None
        
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

def extract_filename_info(file_path):
    """
    Extract row and column information from filename like 'tile_5_12.gltf'
    
    Args:
        file_path (str): Path to the GLTF file
        
    Returns:
        tuple: (row, col) or (None, None) if can't parse
    """
    filename = os.path.basename(file_path)
    try:
        # Extract row and column from filename like 'tile_5_12.gltf'
        parts = filename.replace('.gltf', '').split('_')
        if len(parts) >= 3 and parts[0] == 'tile':
            row = int(parts[1])
            col = int(parts[2])
            return row, col
    except (ValueError, IndexError):
        pass
    return None, None

def load_tiff_background(tiff_path):
    """
    Load a TIFF file and return the data and transform for plotting.
    
    Args:
        tiff_path (str): Path to the TIFF file
        
    Returns:
        tuple: (data, transform, bounds) or (None, None, None) if failed
    """
    if not RASTERIO_AVAILABLE:
        print("rasterio not available, cannot load TIFF background")
        return None, None, None
    
    try:
        with rasterio.open(tiff_path) as src:
            # Read the first band
            data = src.read(1)
            transform = src.transform
            bounds = src.bounds
            print(f"Loaded TIFF: {data.shape}, bounds: {bounds}")
            return data, transform, bounds
    except Exception as e:
        print(f"Error loading TIFF file {tiff_path}: {e}")
        return None, None, None

def visualize_gltf_files(folder_path, output_image=None, show_grid=True, show_tile_bounds=True, tiff_background=None):
    """
    Visualize GLTF files in a matplotlib plot.
    
    Args:
        folder_path (str): Path to folder containing .gltf files
        output_image (str): Path to save the plot image (optional)
        show_grid (bool): Whether to show grid lines
        show_tile_bounds (bool): Whether to show tile boundaries
        tiff_background (str): Path to TIFF file to use as background (optional)
    """
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        print(f"Error: Folder '{folder_path}' does not exist.")
        return
    
    # Find all .gltf files
    gltf_files = list(folder_path.glob("*.gltf"))
    
    if not gltf_files:
        print(f"No .gltf files found in '{folder_path}'")
        return
    
    print(f"Found {len(gltf_files)} GLTF files")
    
    # Extract tile information
    tiles = []
    for file_path in gltf_files:
        tile_info = extract_tile_centers_from_gltf(file_path)
        if tile_info:
            center_x, center_y, tile_width, tile_height = tile_info
            row, col = extract_filename_info(file_path)
            tiles.append({
                'center_x': center_x,
                'center_y': center_y,
                'width': tile_width,
                'height': tile_height,
                'row': row,
                'col': col,
                'filename': file_path.name
            })
        else:
            print(f"Warning: Could not extract tile info from {file_path.name}")
    
    if not tiles:
        print("No valid tile data found in the GLTF files.")
        return
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Load TIFF background if provided
    tiff_data = None
    tiff_transform = None
    tiff_bounds = None
    
    if tiff_background and os.path.exists(tiff_background):
        print(f"Loading TIFF background: {tiff_background}")
        tiff_data, tiff_transform, tiff_bounds = load_tiff_background(tiff_background)
    
    # Calculate plot bounds
    centers_x = [tile['center_x'] for tile in tiles]
    centers_y = [tile['center_y'] for tile in tiles]
    
    min_x, max_x = min(centers_x), max(centers_x)
    min_y, max_y = min(centers_y), max(centers_y)
    
    # If we have TIFF bounds, use them to set the plot extent
    if tiff_bounds:
        plot_min_x = min(min_x, tiff_bounds.left)
        plot_max_x = max(max_x, tiff_bounds.right)
        plot_min_y = min(min_y, tiff_bounds.bottom)
        plot_max_y = max(max_y, tiff_bounds.top)
    else:
        plot_min_x, plot_max_x = min_x, max_x
        plot_min_y, plot_max_y = min_y, max_y
    
    # Add some padding
    padding_x = (plot_max_x - plot_min_x) * 0.05
    padding_y = (plot_max_y - plot_min_y) * 0.05
    
    # Display TIFF background if available
    if tiff_data is not None and tiff_transform is not None:
        # Use rasterio's show function to display the TIFF
        show(tiff_data, ax=ax, transform=tiff_transform, cmap='gray', alpha=0.7)
        print("TIFF background displayed")
    
    # Set plot limits
    ax.set_xlim(plot_min_x - padding_x, plot_max_x + padding_x)
    ax.set_ylim(plot_min_y - padding_y, plot_max_y + padding_y)
    
    # Plot tile centers
    ax.scatter(centers_x, centers_y, c='red', s=50, alpha=0.8, label='GLTF Tile Centers', zorder=10)
    
    # Draw tile boundaries if requested
    if show_tile_bounds:
        for tile in tiles:
            half_w = tile['width'] / 2
            half_h = tile['height'] / 2
            rect = patches.Rectangle(
                (tile['center_x'] - half_w, tile['center_y'] - half_h),
                tile['width'], tile['height'],
                linewidth=2, edgecolor='red', facecolor='none', alpha=0.8, zorder=5
            )
            ax.add_patch(rect)
    
    # Add grid if requested
    if show_grid:
        ax.grid(True, alpha=0.3)
    
    # Add labels and title
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title(f'GLTF Tile Visualization - {len(tiles)} tiles from {folder_path.name}')
    
    # Add legend
    ax.legend()
    
    # Add statistics text
    stats_text = f"""
    Total GLTF Files: {len(tiles)}
    X Range: {min_x:.2f} to {max_x:.2f}
    Y Range: {min_y:.2f} to {max_y:.2f}
    Coverage Area: {(max_x - min_x) * (max_y - min_y):.2f} sq units
    """
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Equal aspect ratio
    ax.set_aspect('equal')
    
    # Show the plot
    plt.tight_layout()
    
    # Save if output path provided
    if output_image:
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_image}")
    
    plt.show()

def analyze_gltf_distribution(tiles):
    """
    Analyze and print statistics about the GLTF tile distribution.
    
    Args:
        tiles (list): List of tile dictionaries
    """
    if not tiles:
        return
    
    print("\n=== GLTF Tile Distribution Analysis ===")
    print(f"Total GLTF files: {len(tiles)}")
    
    # Calculate ranges
    centers_x = [tile['center_x'] for tile in tiles]
    centers_y = [tile['center_y'] for tile in tiles]
    
    print(f"X coordinate range: {min(centers_x):.2f} to {max(centers_x):.2f}")
    print(f"Y coordinate range: {min(centers_y):.2f} to {max(centers_y):.2f}")
    
    # Check for regular grid pattern
    if tiles[0]['row'] is not None and tiles[0]['col'] is not None:
        rows = [tile['row'] for tile in tiles]
        cols = [tile['col'] for tile in tiles]
        print(f"Grid dimensions: {max(rows) - min(rows) + 1} rows x {max(cols) - min(cols) + 1} columns")
        print(f"Row range: {min(rows)} to {max(rows)}")
        print(f"Column range: {min(cols)} to {max(cols)}")
    
    # Check tile size consistency
    widths = [tile['width'] for tile in tiles]
    heights = [tile['height'] for tile in tiles]
    
    if len(set(widths)) == 1 and len(set(heights)) == 1:
        print(f"All tiles have consistent size: {widths[0]} x {heights[0]}")
    else:
        print(f"Tile sizes vary:")
        print(f"  Widths: {min(widths)} to {max(widths)}")
        print(f"  Heights: {min(heights)} to {max(heights)}")

def main():
    """Main function to visualize GLTF tiles from a hardcoded folder path."""
    
    # ===========================================
    # CHANGE THIS PATH TO YOUR GLTF FILES FOLDER
    # ===========================================
    folder_path = "/home/dreamslab/Desktop/antartica351a/tilesgenerate"  # <-- CHANGE THIS LINE
    
    # Optional settings - you can modify these
    output_image = "gltf_visualization.png"  # Set to None to not save image
    show_grid = True                          # Set to False to hide grid
    show_tile_bounds = True                   # Set to False to hide tile boundaries
    show_analysis = True                      # Set to False to hide analysis
    
    # TIFF background (optional) - set to None to not use background image
    tiff_background = "/home/dreamslab/Desktop/antartica351a/351a_modified.tif"  # <-- CHANGE THIS LINE
    
    # ===========================================
    
    print(f"Visualizing GLTF tiles from: {folder_path}")
    print("Note: Converting GLTF tile coordinates to match your background coordinate system")
    print("Background system: X(1617.0 to 8817.0), Y(29228.0 to 33128.0)")
    print("Tile system: 300x300 units, starting from base coordinates")
    print("Formula: center_x = 1617.0 + (col * 300) + 150, center_y = 29228.0 + (row * 300) + 150")
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        print("Please update the 'folder_path' variable in the code.")
        return
    
    # Find all .gltf files
    folder_path = Path(folder_path)
    gltf_files = list(folder_path.glob("*.gltf"))
    
    if not gltf_files:
        print(f"No .gltf files found in '{folder_path}'")
        return
    
    print(f"Found {len(gltf_files)} GLTF files")
    
    # Extract tile information
    tiles = []
    for file_path in gltf_files:
        tile_info = extract_tile_centers_from_gltf(file_path)
        if tile_info:
            center_x, center_y, tile_width, tile_height = tile_info
            row, col = extract_filename_info(file_path)
            tiles.append({
                'center_x': center_x,
                'center_y': center_y,
                'width': tile_width,
                'height': tile_height,
                'row': row,
                'col': col,
                'filename': file_path.name
            })
        else:
            print(f"Warning: Could not extract tile info from {file_path.name}")
    
    if not tiles:
        print("No valid tile data found in the GLTF files.")
        print("This might be because:")
        print("- GLTF files don't contain center coordinates")
        print("- Files don't follow the expected naming convention")
        print("- Files are in a different format")
        return
    
    # Show analysis if requested
    if show_analysis:
        analyze_gltf_distribution(tiles)
    
    # Create visualization
    visualize_gltf_files(
        folder_path,
        output_image=output_image,
        show_grid=show_grid,
        show_tile_bounds=show_tile_bounds,
        tiff_background=tiff_background
    )

if __name__ == "__main__":
    main()
