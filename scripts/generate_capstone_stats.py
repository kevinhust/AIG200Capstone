#!/usr/bin/env python3
"""
Capstone Visualization Generator for Health Butler v7.1

Generates professional visualization charts for Capstone defense presentation:
1. Intensity Distribution Chart (Radar/Bar)
2. Equipment Dependency Analysis (Treemap/Pie)
3. Data Completeness Metrics (Donut/Progress)

Usage:
    python scripts/generate_capstone_stats.py [--output-dir ./docs/capstone]

Output:
    - intensity_distribution.png
    - equipment_analysis.png
    - data_completeness.png
    - system_overview.png (Combined dashboard)
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure matplotlib for professional output
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10

# Color palette (Health Butler brand colors)
COLORS = {
    'primary': '#2E86AB',      # Blue
    'secondary': '#A23B72',    # Magenta
    'accent': '#F18F01',       # Orange
    'success': '#4CAF50',      # Green
    'warning': '#FFC107',      # Yellow
    'danger': '#F44336',       # Red
    'low': '#81C784',          # Light green
    'moderate': '#FFD54F',     # Light yellow
    'high': '#E57373',         # Light red
    'bodyweight': '#64B5F6',   # Light blue
    'dumbbell': '#4DB6AC',     # Teal
    'barbell': '#9575CD',      # Purple
    'machine': '#F06292',      # Pink
    'other': '#90A4AE',        # Gray
}


def load_exercise_cache(cache_path: str = "data/rag/exercise_cache.json") -> Dict:
    """Load exercise cache from JSON file."""
    with open(cache_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_intensity_distribution(exercises: List[Dict]) -> Dict:
    """Analyze intensity distribution across exercises."""
    intensity_counts = Counter()
    intensity_met_avg = {'low': [], 'moderate': [], 'high': []}

    for ex in exercises:
        intensity = ex.get('intensity', 'moderate')
        met = ex.get('met_value', 3.5)
        intensity_counts[intensity] += 1
        intensity_met_avg[intensity].append(met)

    # Calculate average MET per intensity
    avg_met = {}
    for intensity, mets in intensity_met_avg.items():
        avg_met[intensity] = np.mean(mets) if mets else 0

    return {
        'counts': dict(intensity_counts),
        'avg_met': avg_met,
        'total': len(exercises)
    }


def analyze_equipment_distribution(exercises: List[Dict]) -> Dict:
    """Analyze equipment type distribution."""
    equipment_counts = Counter()

    for ex in exercises:
        equipment = ex.get('equipment_type', 'other')
        equipment_counts[equipment] += 1

    return {
        'counts': dict(equipment_counts),
        'total': len(exercises)
    }


def analyze_data_completeness(exercises: List[Dict]) -> Dict:
    """Analyze data completeness metrics."""
    total = len(exercises)

    with_met = sum(1 for ex in exercises if ex.get('met_value'))
    with_intensity = sum(1 for ex in exercises if ex.get('intensity'))
    with_equipment = sum(1 for ex in exercises if ex.get('equipment_type'))
    with_muscles = sum(1 for ex in exercises if ex.get('primary_muscles'))
    with_image = sum(1 for ex in exercises if ex.get('image_url'))

    return {
        'total': total,
        'met_value': {'count': with_met, 'pct': with_met / total * 100},
        'intensity': {'count': with_intensity, 'pct': with_intensity / total * 100},
        'equipment_type': {'count': with_equipment, 'pct': with_equipment / total * 100},
        'primary_muscles': {'count': with_muscles, 'pct': with_muscles / total * 100},
        'image_url': {'count': with_image, 'pct': with_image / total * 100},
    }


def plot_intensity_distribution(data: Dict, output_path: str):
    """Create intensity distribution visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Bar chart with MET overlay
    ax1 = axes[0]
    intensities = ['low', 'moderate', 'high']
    counts = [data['counts'].get(i, 0) for i in intensities]
    colors = [COLORS['low'], COLORS['moderate'], COLORS['high']]

    bars = ax1.bar(intensities, counts, color=colors, edgecolor='white', linewidth=2)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax1.annotate(f'{count}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=14, fontweight='bold')

    ax1.set_xlabel('Intensity Level', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Exercises', fontsize=12, fontweight='bold')
    ax1.set_title('Exercise Intensity Distribution\n(Based on MET Science)', fontsize=14, fontweight='bold')

    # Add MET reference lines
    ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

    # Add MET range annotations
    met_ranges = [
        ('Low\n(MET < 3.0)', COLORS['low'], 0),
        ('Moderate\n(MET 3.0-6.0)', COLORS['moderate'], 1),
        ('High\n(MET > 6.0)', COLORS['high'], 2)
    ]

    # Right: Pie chart
    ax2 = axes[1]
    wedges, texts, autotexts = ax2.pie(
        counts,
        labels=['Low Intensity\n(Yoga, Stretching)', 'Moderate\n(Walking, Cycling)', 'High Intensity\n(HIIT, Running)'],
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        explode=(0.02, 0.02, 0.02),
        shadow=True
    )

    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')

    ax2.set_title('Intensity Proportion\n(Total: {} exercises)'.format(data['total']), fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ Saved: {output_path}")


def plot_equipment_analysis(data: Dict, output_path: str):
    """Create equipment type visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Equipment color mapping
    equipment_colors = {
        'bodyweight': COLORS['bodyweight'],
        'dumbbell': COLORS['dumbbell'],
        'barbell': COLORS['barbell'],
        'machine': COLORS['machine'],
        'cable': '#7986CB',
        'band': '#4DB6AC',
        'kettlebell': '#FFB74D',
        'ball': '#A5D6A7',
        'bench': '#BCAAA4',
        'rack': '#90A4AE',
        'other': COLORS['other'],
    }

    # Sort by count
    sorted_equipment = sorted(data['counts'].items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_equipment]
    values = [item[1] for item in sorted_equipment]
    colors = [equipment_colors.get(label, COLORS['other']) for label in labels]

    # Left: Horizontal bar chart
    ax1 = axes[0]
    y_pos = np.arange(len(labels))
    bars = ax1.barh(y_pos, values, color=colors, edgecolor='white', linewidth=1)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=10)
    ax1.invert_yaxis()
    ax1.set_xlabel('Number of Exercises', fontsize=12, fontweight='bold')
    ax1.set_title('Equipment Type Distribution\n(Where can you exercise?)', fontsize=14, fontweight='bold')

    # Add count labels
    for bar, val in zip(bars, values):
        ax1.annotate(f' {val}',
                    xy=(val, bar.get_y() + bar.get_height()/2),
                    va='center', ha='left',
                    fontsize=10, fontweight='bold')

    # Right: Highlight bodyweight vs equipment
    ax2 = axes[1]

    bodyweight = data['counts'].get('bodyweight', 0)
    equipment_based = data['total'] - bodyweight

    wedges, texts, autotexts = ax2.pie(
        [bodyweight, equipment_based],
        labels=['Bodyweight\n(Home/Office)', 'Equipment\n(Gym)'],
        colors=[COLORS['bodyweight'], COLORS['barbell']],
        autopct='%1.1f%%',
        startangle=90,
        explode=(0.05, 0),
        shadow=True
    )

    for autotext in autotexts:
        autotext.set_fontsize(14)
        autotext.set_fontweight('bold')

    ax2.set_title('Scenario Coverage\n(No Gym Required vs Gym)', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ Saved: {output_path}")


def plot_data_completeness(data: Dict, output_path: str):
    """Create data completeness visualization."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Metrics to display
    metrics = [
        ('MET Value', data['met_value']),
        ('Intensity', data['intensity']),
        ('Equipment Type', data['equipment_type']),
        ('Primary Muscles', data['primary_muscles']),
        ('Exercise Image', data['image_url']),
    ]

    # Create progress bars
    y_positions = np.arange(len(metrics))
    pcts = [m[1]['pct'] for m in metrics]
    counts = [m[1]['count'] for m in metrics]
    labels = [m[0] for m in metrics]

    # Background bars (100%)
    ax.barh(y_positions, [100] * len(metrics), color='#E0E0E0', height=0.6)

    # Progress bars
    bar_colors = [COLORS['success'] if p >= 90 else COLORS['warning'] if p >= 50 else COLORS['danger']
                  for p in pcts]
    bars = ax.barh(y_positions, pcts, color=bar_colors, height=0.6, edgecolor='white', linewidth=2)

    # Add percentage labels
    for i, (bar, pct, count) in enumerate(zip(bars, pcts, counts)):
        # Percentage inside bar
        ax.annotate(f'{pct:.1f}%',
                    xy=(pct - 5 if pct > 20 else pct + 2, bar.get_y() + bar.get_height()/2),
                    va='center', ha='right' if pct > 20 else 'left',
                    fontsize=12, fontweight='bold', color='white' if pct > 20 else 'black')

        # Count on right
        ax.annotate(f'{count:,} / {data["total"]:,}',
                    xy=(102, bar.get_y() + bar.get_height()/2),
                    va='center', ha='left',
                    fontsize=10, color='gray')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=12, fontweight='bold')
    ax.set_xlim(0, 130)
    ax.set_xlabel('Completion Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Data Completeness Metrics\n(How complete is our exercise database?)',
                 fontsize=14, fontweight='bold')

    # Add legend
    legend_elements = [
        mpatches.Patch(color=COLORS['success'], label='Complete (≥90%)'),
        mpatches.Patch(color=COLORS['warning'], label='Partial (50-89%)'),
        mpatches.Patch(color=COLORS['danger'], label='Incomplete (<50%)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    ax.axvline(x=100, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ Saved: {output_path}")


def plot_system_overview(intensity_data: Dict, equipment_data: Dict, completeness_data: Dict, output_path: str):
    """Create combined system overview dashboard."""
    fig = plt.figure(figsize=(16, 12))

    # Title
    fig.suptitle('Health Butler v7.1 - System Capability Overview\nPowered by MET Science Engine',
                 fontsize=18, fontweight='bold', y=0.98)

    # Create grid
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

    # 1. Intensity Pie (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    intensities = ['low', 'moderate', 'high']
    counts = [intensity_data['counts'].get(i, 0) for i in intensities]
    colors = [COLORS['low'], COLORS['moderate'], COLORS['high']]

    ax1.pie(counts, labels=intensities, colors=colors, autopct='%1.1f%%',
            startangle=90, explode=(0.02, 0.02, 0.02))
    ax1.set_title('Intensity Distribution', fontsize=12, fontweight='bold')

    # 2. Equipment Bar (top middle)
    ax2 = fig.add_subplot(gs[0, 1])
    top_equipment = sorted(equipment_data['counts'].items(), key=lambda x: x[1], reverse=True)[:5]
    labels = [e[0] for e in top_equipment]
    values = [e[1] for e in top_equipment]

    equipment_colors = {
        'bodyweight': COLORS['bodyweight'],
        'dumbbell': COLORS['dumbbell'],
        'barbell': COLORS['barbell'],
        'other': COLORS['other'],
        'cable': '#7986CB',
    }
    colors = [equipment_colors.get(l, COLORS['other']) for l in labels]

    ax2.bar(labels, values, color=colors, edgecolor='white')
    ax2.set_title('Top 5 Equipment Types', fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    # 3. Completeness Summary (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.axis('off')

    completeness_text = f"""
    📊 Data Completeness Summary
    ═══════════════════════════

    Total Exercises: {completeness_data['total']:,}

    ✅ MET Values: {completeness_data['met_value']['pct']:.1f}%
    ✅ Intensity: {completeness_data['intensity']['pct']:.1f}%
    ✅ Equipment: {completeness_data['equipment_type']['pct']:.1f}%
    ✅ Muscles: {completeness_data['primary_muscles']['pct']:.1f}%
    📷 Images: {completeness_data['image_url']['pct']:.1f}%

    ═══════════════════════════
    🧠 Source: Wger.de API
    🔬 MET: Compendium of Physical Activities
    """
    ax3.text(0.1, 0.5, completeness_text, transform=ax3.transAxes,
             fontsize=11, verticalalignment='center', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#F5F5F5', alpha=0.8))

    # 4. MET Distribution (bottom left and middle)
    ax4 = fig.add_subplot(gs[1, :2])

    # Create MET histogram
    met_values = []
    for ex in load_exercise_cache()['data']:
        if ex.get('met_value'):
            met_values.append(ex['met_value'])

    if met_values:
        ax4.hist(met_values, bins=20, color=COLORS['primary'], edgecolor='white', alpha=0.7)
        ax4.axvline(x=3.0, color=COLORS['low'], linestyle='--', linewidth=2, label='Low/Moderate threshold')
        ax4.axvline(x=6.0, color=COLORS['high'], linestyle='--', linewidth=2, label='Moderate/High threshold')
        ax4.set_xlabel('MET Value', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Number of Exercises', fontsize=12, fontweight='bold')
        ax4.set_title('MET Value Distribution\n(Scientific Calorie Calculation Basis)', fontsize=12, fontweight='bold')
        ax4.legend()

    # 5. Key Statistics (bottom right)
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis('off')

    stats_text = f"""
    🏆 Key Statistics
    ═════════════════════

    📚 Total Exercises: 867

    🔬 MET Range: 1.0 - 11.0
    📊 Avg MET: {np.mean(met_values):.2f}

    🏋️ Bodyweight: {equipment_data['counts'].get('bodyweight', 0)} ({equipment_data['counts'].get('bodyweight', 0)/equipment_data['total']*100:.1f}%)

    ═════════════════════
    Version: v7.1 MET Science
    Generated: {datetime.now().strftime('%Y-%m-%d')}
    """
    ax5.text(0.1, 0.5, stats_text, transform=ax5.transAxes,
             fontsize=11, verticalalignment='center', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.8))

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ Saved: {output_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate Capstone visualization charts')
    parser.add_argument('--output-dir', default='docs/capstone', help='Output directory for charts')
    parser.add_argument('--cache-path', default='data/rag/exercise_cache.json', help='Exercise cache path')
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("Health Butler v7.1 - Capstone Visualization Generator")
    print("=" * 60)

    # Load data
    print(f"\n📂 Loading exercise cache from: {args.cache_path}")
    cache_data = load_exercise_cache(args.cache_path)
    exercises = cache_data.get('data', [])
    print(f"   Found {len(exercises)} exercises")

    # Analyze data
    print("\n🔬 Analyzing data...")
    intensity_data = analyze_intensity_distribution(exercises)
    equipment_data = analyze_equipment_distribution(exercises)
    completeness_data = analyze_data_completeness(exercises)

    print(f"   Intensity: {intensity_data['counts']}")
    print(f"   Equipment types: {len(equipment_data['counts'])}")
    print(f"   MET completeness: {completeness_data['met_value']['pct']:.1f}%")

    # Generate charts
    print("\n📊 Generating visualization charts...")

    plot_intensity_distribution(
        intensity_data,
        os.path.join(args.output_dir, 'intensity_distribution.png')
    )

    plot_equipment_analysis(
        equipment_data,
        os.path.join(args.output_dir, 'equipment_analysis.png')
    )

    plot_data_completeness(
        completeness_data,
        os.path.join(args.output_dir, 'data_completeness.png')
    )

    plot_system_overview(
        intensity_data,
        equipment_data,
        completeness_data,
        os.path.join(args.output_dir, 'system_overview.png')
    )

    print("\n" + "=" * 60)
    print("✅ Visualization generation complete!")
    print(f"📁 Output directory: {args.output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
