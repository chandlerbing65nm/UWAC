import librosa
import glob
from torch.utils.data import Dataset, DataLoader
import os
import numpy as np
import torch
from scipy.signal import resample
from itertools import chain
import random
import torchaudio
import pickle


def save_pickle(obj, fname):
    # print("Save pickle at " + fname)
    with open(fname, "wb") as f:
        pickle.dump(obj, f)


def load_pickle(fname):
    # print("Load pickle at " + fname)
    with open(fname, "rb") as f:
        res = pickle.load(f)
    return res


def load_audio(path, sr=None):
    y, _ = librosa.load(path, sr=None)
    y = resample(y, num=sr*2)
    return y

 
def load_noise(path):
    y, sample = librosa.load(path, sr=64000)
    dur1 = librosa.get_duration(y, sample)
    if dur1 > 2:
        n_samples = int(2 * sample)
        audio = y[:n_samples]
    elif dur1 < 2:
        duration = 2
        samples_need = int(sample*duration)
        samples_to_pad = max(samples_need - len(y), 0)
        padded_signal = np.pad(y, (0, samples_to_pad), 'constant', constant_values=0)
        audio = padded_signal
    else:
        audio= y

    return audio

def get_noisename():
    path = '/mnt/fast/nobackup/users/mc02229/noise/vd_noise'
    wav_dir = os.path.join(path, '*.wav')
    return glob.glob(wav_dir)

def get_wav_name(split='strong', data_path='./'):
    """
    params: str
        middle, none, strong, weak
    """
    path = data_path #
    audio = []
    l1 = os.listdir(path)
    for dir in l1:
        l2 = os.listdir(os.path.join(path, dir))
        for dir1 in l2:
            wav_dir = os.path.join(path, dir, dir1, split, '*.wav')
            audio.append(glob.glob(wav_dir))
    return list(chain.from_iterable(audio))




def data_generator(seed, test_sample_per_class, data_path='./'):
    """
    class to label mapping:
    none: 0
    strong: 1
    middle: 2
    weak: 3
    """

    random_state = np.random.RandomState(seed)
    strong_list = get_wav_name(split='strong', data_path=data_path)
    medium_list = get_wav_name(split='medium', data_path=data_path)
    weak_list = get_wav_name(split='weak', data_path=data_path)
    none_list = get_wav_name(split='none', data_path=data_path)

    random_state.shuffle(strong_list)
    random_state.shuffle(medium_list)
    random_state.shuffle(weak_list)
    random_state.shuffle(none_list)

    strong_test = strong_list[:test_sample_per_class]
    medium_test = medium_list[:test_sample_per_class]
    weak_test = weak_list[:test_sample_per_class]
    none_test = none_list[:test_sample_per_class]

    strong_val = strong_list[test_sample_per_class:2*test_sample_per_class]
    medium_val = medium_list[test_sample_per_class:2*test_sample_per_class]
    weak_val = weak_list[test_sample_per_class:2*test_sample_per_class]
    none_val = none_list[test_sample_per_class:2*test_sample_per_class]

    strong_train = strong_list[2*test_sample_per_class:]
    medium_train = medium_list[2*test_sample_per_class:]
    weak_train = weak_list[2*test_sample_per_class:]
    none_train = none_list[2*test_sample_per_class:]

    train_dict = []
    test_dict = []
    val_dict = []

    for wav in strong_train:
        train_dict.append([wav, 1])
    
    for wav in medium_train:
        train_dict.append([wav, 2])
    
    for wav in weak_train:
        train_dict.append([wav, 3])

    for wav in none_train:
        train_dict.append([wav, 0])
    
    for wav in strong_test:
        test_dict.append([wav, 1])
    
    for wav in medium_test:
        test_dict.append([wav, 2])
    
    for wav in weak_test:
        test_dict.append([wav, 3])

    for wav in none_test:
        test_dict.append([wav, 0])

    for wav in strong_val:
        val_dict.append([wav, 1])

    for wav in medium_val:
        val_dict.append([wav, 2])

    for wav in weak_val:
        val_dict.append([wav, 3])

    for wav in none_val:
        val_dict.append([wav, 0])

    random_state.shuffle(train_dict)

    return train_dict, test_dict, val_dict


class Fish_Voice_Dataset(Dataset):
    def __init__(self, sample_rate, seed, split='train', data_path='./'):
        """
        split: train or test
        if sample_rate=None, read audio with the default sr
        """
        self.seed = seed
        self.split = split
        self.data_path = data_path

        train_dict, test_dict, val_dict = data_generator(self.seed, test_sample_per_class=700, data_path=self.data_path)

        if self.split == 'train':
            self.data_dict = train_dict
        elif self.split == 'test':
            self.data_dict = test_dict
        elif self.split == 'val':
            self.data_dict = val_dict
        self.sample_rate = sample_rate

    def __len__(self):

        return len(self.data_dict)
    
    def __getitem__(self, index):

        wav_name, target = self.data_dict[index]
        wav = load_audio(wav_name, sr=self.sample_rate)
        wav = np.array(wav)
        # change 'eye(num)' if using different class nums
        target = np.eye(4)[target]

        data_dict = {'audio_name': wav_name, 'waveform': wav, 'target': target}

        return data_dict


def collate_fn(batch):
    wav_name = [data['audio_name'] for data in batch]
    wav = [data['waveform'] for data in batch]
    target = [data['target'] for data in batch]
    # wav = torch.stack([data['waveform'] for data in batch])
    wav = torch.FloatTensor(np.array(wav))
    target = torch.FloatTensor(np.array(target))

    return {'audio_name': wav_name, 'waveform': wav, 'target': target}


def get_dataloader(split,
                   batch_size,
                   sample_rate,
                   seed,
                   shuffle=False,
                   drop_last=False,
                   num_workers=4,
                   data_path='./',
                   sampler=None):

    dataset = Fish_Voice_Dataset(split=split, sample_rate=sample_rate, seed=seed, data_path=data_path)

    dataloader = DataLoader(dataset=dataset, batch_size=batch_size,
                      shuffle=shuffle, drop_last=drop_last,
                      num_workers=num_workers, sampler=sampler, collate_fn=collate_fn)

    return dataset, dataloader


if __name__ == '__main__':
    train_loader = get_dataloader(split='train', batch_size=1, sample_rate=64000, seed=25)
    from tqdm import tqdm
    for item in tqdm(train_loader):
        print(item['audio_name'])
        print(item['waveform'].shape)
        print(item['target'].shape)
        break

    # noise_name = get_noisename()
    # print(noise_name)
    # print(len(noise_name))