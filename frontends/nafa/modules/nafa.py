import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import matplotlib.pyplot as plt

EPS = 1e-12
RESCALE_INTERVEL_MIN = 1e-4
RESCALE_INTERVEL_MAX = 1 - 1e-4

class FrameAugment(nn.Module):
    def __init__(self, seq_len, feat_dim, temperature=0.2, frame_reduction_ratio=None, activation_type="gumbel_softmax", device='cuda'):
        """
        Initialize the FrameAugment module with an option for different augmenting paths.

        Args:
            seq_len (int): The length of the input sequence.
            feat_dim (int): The dimensionality of each feature.
            temperature (float): The temperature for the Gumbel-Softmax. Lower values make it sharper.
            frame_reduction_ratio (float): Ratio to reduce the sequence length (0 < ratio <= 1).
            activation_type (str): Type of activation to use. Options: "gumbel_softmax", "sigmoid", "bernoulli", "softmax", "temp_softmax".
        """
        super(FrameAugment, self).__init__()

        # Compute reduced sequence length
        self.seq_len = seq_len
        self.frame_reduction_ratio = frame_reduction_ratio

        if frame_reduction_ratio is not None:
            assert 0 < frame_reduction_ratio <= 1, "frame_reduction_ratio must be between 0 and 1"
            self.reduced_len = max(1, int(seq_len * (1 - frame_reduction_ratio)))
        else:
            self.reduced_len = self.seq_len

        # noise templates for augmentation (initialized randomly)
        self.noise_template = torch.randn(1, self.reduced_len, seq_len).to(device=device)

        self.temperature = temperature
        self.activation_type = activation_type


    def forward(self, feature):
        """
        Forward function that computes an augmented feature representation
        using a differentiable FrameAugment mechanism conditioned on the score tensor.

        Args:
            feature (Tensor): A tensor representing the features.

        Returns:
            out_feature (Tensor): augmented output feature.
        """
        batch_size, seq_len, feat_dim = feature.size()

        # Step 1: Create a mixing matrix matrix from the noise template
        mixing_matrix = self.noise_template.expand(batch_size, -1, -1)

        # Step 2: Apply selected activation to get a differentiable augmenting path
        augmenting_path = self.compute_augmenting_path(mixing_matrix)

        # Step 3: augment the features based on the augmenting path
        augmented_feature = self.apply_augmenting(feature, augmenting_path)

        return augmented_feature

    def compute_augmenting_path(self, mixing_matrix):
        """
        Compute an augmenting matrix (augmenting path) using the selected activation function.

        Args:
            mixing_matrix (Tensor): A tensor of shape [batch, seq_len, seq_len].

        Returns:
            augmenting_path (Tensor): An augmenting path matrix.
        """
        if self.activation_type == "gumbel_softmax":
            # Gumbel-Softmax path
            logits = -mixing_matrix
            return self.gumbel_softmax_sample(logits, temperature=self.temperature)
        elif self.activation_type == "sigmoid":
            # Sigmoid activation
            logits = -mixing_matrix
            return torch.sigmoid(logits)
        elif self.activation_type == "bernoulli":
            # Bernoulli sampling (requires logits between 0 and 1)
            logits = mixing_matrix
            return torch.bernoulli(logits)
        elif self.activation_type == "softmax":
            # Standard softmax
            logits = -mixing_matrix
            return F.softmax(logits, dim=-1)
        elif self.activation_type == "temp_softmax":
            # Softmax with temperature scaling
            logits = -mixing_matrix
            return F.softmax(logits / self.temperature, dim=-1)
        else:
            raise ValueError(f"Unsupported activation type: {self.activation_type}")

    def gumbel_softmax_sample(self, logits, temperature=1.0):
        """
        Samples from the Gumbel-Softmax distribution with the specified temperature.

        Args:
            logits (Tensor): Input logits.
            temperature (float): Temperature for Gumbel-Softmax. Lower temperatures make it more like hard selection.

        Returns:
            Tensor: Softmax with Gumbel noise added.
        """
        # Sample Gumbel noise
        gumbel_noise = -torch.log(-torch.log(torch.rand_like(logits) + EPS) + EPS)

        # Add Gumbel noise and apply softmax with temperature scaling
        return F.softmax((logits + gumbel_noise) / temperature, dim=-1)

    def apply_augmenting(self, feature, augmenting_path):
        """
        Apply the augmenting to the feature using the augmenting path.

        Args:
            feature (Tensor): A tensor of shape [batch, seq_len, feat_dim].
            augmenting_path (Tensor): A tensor of shape [batch, seq_len, seq_len].

        Returns:
            augmented_feature (Tensor): augmented feature of shape [batch, seq_len, feat_dim].
        """
        # Use einsum to apply augmenting across the sequence length dimension
        # Adjusted indices to match the dimensions
        augmented_feature = torch.einsum('bij,bjf->bif', augmenting_path, feature)  # [batch, reduced_len, feat_dim]

        return augmented_feature


class NAFA(nn.Module):
    def __init__(self, in_t_dim, in_f_dim):
        super().__init__()
        self.input_seq_length = in_t_dim
        self.input_f_dim = in_f_dim
        
        self.frame_augment = FrameAugment(
            seq_len=self.input_seq_length, 
            feat_dim=self.input_f_dim,
            temperature=0.2, 
            frame_reduction_ratio=0.6,
            activation_type='sigmoid',  # Set the activation type
            device='cuda'
        )

    def forward(self, x):
        ret = {}

        augment_frame = self.frame_augment(x.exp())
        augment_frame = torch.log(augment_frame + EPS)

        # Final outputs
        ret["x"] = x
        ret["features"] = augment_frame
        ret["dummy"] = torch.tensor(0.0, device=x.device)
        ret["total_loss"] = ret["dummy"]

        return ret
