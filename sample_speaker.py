"""Sampling code for the parrot.

Loads the trained model and samples.
"""

import numpy
import os
import cPickle
import logging

from blocks.serialization import load_parameters
from blocks.model import Model

from blizzard import speaker_conditioned_stream
from model import SpeakerConditionedParrot
from utils import speaker_conditioned_sample_parse

from io_funcs.binary_io import BinaryIOCollection

logging.basicConfig()

parser = speaker_conditioned_sample_parse()
args = parser.parse_args()

with open(os.path.join(
        args.save_dir, 'config',
        args.experiment_name + '.pkl')) as f:
    saved_args = cPickle.load(f)

with open(os.path.join(
        args.save_dir, "pkl",
        "best_" + args.experiment_name + ".tar"), 'rb') as src:
    parameters = load_parameters(src)

# test_stream = speaker_conditioned_stream(
#     ('test',), args.num_samples, args.num_steps, sorting_mult=1)

# features_tr, features_mask_tr, labels_tr, spk_tr, start_flag_tr = \
#     next(test_stream.get_epoch_iterator())

numpy.random.seed(1)
spk_tr = numpy.random.random_integers(
    1, saved_args.num_speakers - 1, (args.num_samples, 1))
spk_tr = numpy.int8(spk_tr)

print '/Tmp/sotelo/data/vctk/new_sentences_no_silence.npy'
labels_tr = numpy.load('/Tmp/sotelo/data/vctk/new_sentences_no_silence.npy')
lengths_tr = [len(x) for x in labels_tr]
max_length = max(lengths_tr)
features_mask_tr = numpy.zeros(
    (args.num_samples, max_length), dtype='float32')
padded_labels_tr = numpy.zeros(
    (args.num_samples, max_length, saved_args.input_dim), dtype='float32')

for i, sample in enumerate(labels_tr):
    padded_labels_tr[i, :len(sample)] = sample
    features_mask_tr[i, :len(sample)] = 1.

labels_tr = padded_labels_tr

features_mask_tr = features_mask_tr.swapaxes(0, 1)
labels_tr = labels_tr.swapaxes(0, 1)

if args.speaker_id:
    spk_tr = spk_tr * 0 + args.speaker_id

if args.mix:
    spk_tr = spk_tr * 0
    parameters['/parrot/lookuptable.W'][0] = \
        args.mix * parameters['/parrot/lookuptable.W'][10] + \
        (1 - args.mix) * parameters['/parrot/lookuptable.W'][11]

parrot_args = {
    'input_dim': saved_args.input_dim,
    'output_dim': saved_args.output_dim,
    'rnn_h_dim': saved_args.rnn_h_dim,
    'readouts_dim': saved_args.readouts_dim,
    'speaker_dim': saved_args.speaker_dim,
    'num_speakers': saved_args.num_speakers,
    'name': 'parrot'}

parrot = SpeakerConditionedParrot(**parrot_args)

features, features_mask, labels, speaker, start_flag = \
    parrot.symbolic_input_variables()

cost, extra_updates = parrot.compute_cost(
    features, features_mask, labels, speaker, start_flag, args.num_samples)


model = Model(cost)
model.set_parameter_values(parameters)

x_sample = parrot.sample_model(
    labels_tr, features_mask_tr, spk_tr, args.num_samples)

x_sample = x_sample[0].swapaxes(0, 1)

io_fun = BinaryIOCollection()

gen_file_list = []
for i, this_sample in enumerate(x_sample):
    this_sample = this_sample[:features_mask_tr.sum(axis=0)[i]]
    file_name = os.path.join(
        args.save_dir, 'samples',
        args.samples_name + '_' + str(i) + ".cmp")
    io_fun.array_to_binary_file(this_sample, file_name)
    gen_file_list.append(file_name)

print "End of sampling."

# importing from merlin
import configuration
cfg=configuration.cfg
config_file='/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/conf/acoustic_vctk.conf'
cfg.configure(config_file, use_logging=False)

from frontend.parameter_generation import ParameterGeneration
from frontend.mean_variance_norm import MeanVarianceNorm

#norm_info_file = '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/norm_info_mgc_lf0_vuv_bap_187_MVN.dat'
#norm_info_file = '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/norm_info_mgc_lf0_vuv_bap_63_MVN.dat'
norm_info_file = '/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/experiments/vctk/acoustic_model/data/norm_info_mgc_lf0_vuv_bap_63_MVN.dat'
fid = open(norm_info_file, 'rb')
cmp_min_max = numpy.fromfile(fid, dtype=numpy.float32)
fid.close()
cmp_min_max = cmp_min_max.reshape((2, -1))
cmp_min_vector = cmp_min_max[0, ]
cmp_max_vector = cmp_min_max[1, ]

# assert saved_args.output_dim == 63
denormaliser = MeanVarianceNorm(feature_dimension=saved_args.output_dim)
denormaliser.feature_denormalisation(
    gen_file_list, gen_file_list, cmp_min_vector, cmp_max_vector)

# var_file_dict = {
#     'mgc': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/mgc_180',
#     'vuv': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/vuv_1',
#     'lf0': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/lf0_3',
#     'bap': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/bap_3'}

# var_file_dict = {
#     'mgc': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/mgc_60',
#     'vuv': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/vuv_1',
#     'lf0': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/lf0_1',
#     'bap': '/Tmp/sotelo/code/merlin/egs/slt_arctic/s1/experiments/slt_arctic_full/acoustic_model/data/var/bap_1'}

var_file_dict = {
    'mgc': '/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/experiments/vctk/acoustic_model/data/var/mgc_60',
    'vuv': '/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/experiments/vctk/acoustic_model/data/var/vuv_1',
    'lf0': '/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/experiments/vctk/acoustic_model/data/var/lf0_1',
    'bap': '/Tmp/sotelo/code/merlin/egs/build_your_own_voice/s1/experiments/vctk/acoustic_model/data/var/bap_1'}

cfg.cmp_dim = 63

cfg.out_dimension_dict = {'bap': 1, 'lf0': 1, 'mgc': 60, 'vuv': 1}

generator = ParameterGeneration(
    gen_wav_features=cfg.gen_wav_features,
    enforce_silence=cfg.enforce_silence)
generator.acoustic_decomposition(
    gen_file_list,
    cfg.cmp_dim,
    cfg.out_dimension_dict,
    cfg.file_extension_dict,
    var_file_dict,
    do_MLPG=False,
    cfg=cfg)

# generator = ParameterGeneration(
#     gen_wav_features=cfg.gen_wav_features,
#     enforce_silence=cfg.enforce_silence)
# generator.acoustic_decomposition(
#     gen_file_list,
#     saved_args.output_dim,
#     {'mgc': 180, 'vuv': 1, 'lf0': 3, 'bap': 3},
#     {'mgc': '.mgc', 'bap': '.bap', 'lf0': '.lf0', 'cmp': '.cmp'},
#     var_file_dict,
#     do_MLPG=False,
#     cfg=None)

from generate import generate_wav

generate_wav(
    os.path.join(args.save_dir, 'samples'),
    [args.samples_name + '_' + str(i) for i in range(args.num_samples)], cfg)