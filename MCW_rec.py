%%writefile MCW_rec.py
import torch
from torch import nn

class FeatureExtractor(nn.Module):
	def __init__(self, vocab_size, embedding_size, hidden_size, output_size, pad_index=-1, layers=1, dropout=0, bidirectional=False):
		super().__init__()
		self.bidirectional = bidirectional
		self.embedding_layer = nn.Embedding(vocab_size, embedding_size, padding_idx=pad_index)
		self.recurrent_module = nn.LSTM(embedding_size, hidden_size, bidirectional=bidirectional, dropout=dropout, num_layers=layers)
		out_input_size = hidden_size*2 if bidirectional else hidden_size
		self.feature_extractor = nn.Sequential(
			nn.Dropout(dropout),
			nn.Linear(out_input_size, 32),
			nn.Dropout(dropout),
			nn.Linear(32, 16)
		)
		self.output_layer = nn.Sequential(
			nn.Dropout(dropout),
			nn.Linear(16, output_size)   
		)
	def load(self, path):
		self.load_state_dict(torch.load(path, map_location=torch.device('cpu')))
	def forward(self, x):
		x = self.embedding_layer(x) # batch_size, seq_length --> batch_size, seq_length, emb_dim
		# Swap the first two dimensions to prepare x for the recurrent module
		x = x.permute(1,0,2) # bs, sl, ed --> sl, bs, ed
		_, (_, out) = self.recurrent_module(x) # sl, bs, ed --> bs, hidden_size
		# out dimension 0: l1f, l1b, l2f, l2b, ...
		if (self.bidirectional):
		  out = torch.cat((out[-2,:,:], out[-1,:,:]), dim=1)
		else:
		  out = out[-1]
		features = self.feature_extractor(out)
		return self.output_layer(features), features
	def extract_features(self, x):
		x = self.embedding_layer(x) # batch_size, seq_length --> batch_size, seq_length, emb_dim
		# Swap the first two dimensions to prepare x for the recurrent module
		x = x.permute(1,0,2) # bs, sl, ed --> sl, bs, ed
		_, (_, out) = self.recurrent_module(x) # sl, bs, ed --> bs, hidden_size
		# out dimension 0: l1f, l1b, l2f, l2b, ...
		if (self.bidirectional):
		  out = torch.cat((out[-2,:,:], out[-1,:,:]), dim=1)
		else:
		  out = out[-1]
		features = self.feature_extractor(out)
		return features.detach().numpy()