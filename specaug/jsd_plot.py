import matplotlib.pyplot as plt
import numpy as np

# Data
datasets = ['AFFIA3k', 'UFFIA', 'MRS-FFIA']
frame_mix = [0.00411, 0.00219, 0.00097]
diff_res = [0.62540, 0.61740, 0.61440]
spec_mix = [0.01456, 0.01436, 0.01362]
spec_augment = [0.00518, 0.00721, 0.00753]

# Bar width and positions
x = np.arange(len(datasets))
width = 0.2

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

# Plot bars with colors
bars_frame_mix = ax.bar(x - 1.5 * width, frame_mix, width, label='FrameMix (ours)', color='blue')
bars_diff_res = ax.bar(x - 0.5 * width, [0.017] * len(datasets), width, label='DiffRes (AAAI\'24)', color='red')
bars_spec_mix = ax.bar(x + 0.5 * width, spec_mix, width, label='SpecMix (Interspeech\'21)', color='green')
bars_spec_augment = ax.bar(x + 1.5 * width, spec_augment, width, label='SpecAugment (Interspeech\'19)', color='orange')

# Annotate actual DiffRes values above the bars
for i, val in enumerate(diff_res):
    ax.text(x[i] - 0.5 * width, 0.017, f"{val:.5f}", ha='center', va='bottom', fontsize=9)

# Labels and title
ax.set_xlabel('Datasets', fontsize=12)
ax.set_ylabel('Jensen-Shannon Divergence', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(datasets, fontsize=11)
ax.set_ylim(0, 0.017)

# Legend
ax.legend()

# Grid
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Save plot as a figure
plt.tight_layout()
plt.savefig("jsd_plot.png", dpi=300)