#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

import torch
from torch import Tensor
from torchoutil import generate_square_subsequent_mask, tensor_to_pad_mask

from dcase24t6.nn.decoding.common import AACDecoder


def teacher_forcing(
    decoder: AACDecoder,
    *,
    pad_id: int,
    frame_embs: Tensor,
    frame_embs_pad_mask: Tensor,
    caps_in: Tensor,
    caps_in_pad_mask: Optional[Tensor] = None,
    caps_in_attn_mask: Optional[Tensor] = None,
) -> Tensor:
    """Compute logits using previous references tokens.

    :param decoder: The decoder part of the model.
    :param pad_id: Padding token id.
    :param frame_embs: (bsize, frame_emb_size, n_frames)
    :param frame_embs_pad_mask: (bsize, n_frames)
    :param caps_in: (bsize, caps_size) or (bsize, caps_size, caps_emb_size)
    :param caps_in_pad_mask: (bsize, caps_size) or None.
        If None, this mask will be inferred from caps_in.
    :param caps_in_attn_mask: (caps_size, caps_size) or None.
        If None, this mask will be a batch of upper triangular matrix of -inf, which avoid seeing the future tokens.
    :returns: (max_pred_size, bsize, vocab_size)
    """
    # (bsize, embed_len, n_frames) -> (n_frames, bsize, embed_len)
    frame_embs = frame_embs.permute(2, 0, 1)

    if caps_in_pad_mask is None:
        if caps_in.is_floating_point():
            raise ValueError(
                "Invalid combinaison of arguments captions_pad_mask=None with captions floating-point embs."
            )
        caps_in_pad_mask = tensor_to_pad_mask(caps_in, pad_value=pad_id)

    if caps_in_attn_mask is None:
        caps_size = caps_in.shape[1]
        caps_in_attn_mask = generate_square_subsequent_mask(
            caps_size,
            device=caps_in.device,
            dtype=torch.bool,
        )

    if not caps_in.is_floating_point():
        caps_in = caps_in.permute(1, 0)
    else:
        caps_in = caps_in.permute(1, 0, 2)

    logits, loss = decoder(
        frame_embs=frame_embs,
        frame_embs_attn_mask=None,
        frame_embs_pad_mask=frame_embs_pad_mask,
        caps_in=caps_in,
        caps_in_attn_mask=caps_in_attn_mask,
        caps_in_pad_mask=caps_in_pad_mask,
    )

    # permute: (caps_size, bsize, vocab_size) -> (bsize, vocab_size, caps_size)
    logits = logits.permute(1, 2, 0)
    return logits, loss
