import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn import datasets

import dataset
from toy.basics import Net, ToyClassifier
from active_query import HeuristicRelabel


moons = True
n_positive = 10000
n_negative = 10000
n = n_positive + n_negative

pho_p = 0.5
pho_n = 0
pho_p_c = pho_p
pho_n_c = pho_n

learning_rate = 5e-3
weight_decay = 1e-3

convex_epochs = 500
retrain_epochs = 12000

init_weight = 1
init_size = 90
kcenter = False

corr_times = 8
corr_size = 3

load = False
save = False


def create_new_classifier():
    model = Net()
    cls = ToyClassifier(
            model,
            pho_p=pho_p_c,
            pho_n=pho_n_c,
            lr=learning_rate,
            weight_decay=weight_decay)
    return cls


if moons:
    x_all, y_all = datasets.make_moons(n, noise=0.07)
else:
    x_all, y_all = datasets.make_circles(n, noise=0.03)
y_all = (y_all*2-1).reshape(-1, 1)

if kcenter:
    unlabeled_set, labeled_set = dataset.datasets_initialization_kcenter(
        x_all, y_all, init_size, init_weight, pho_p, pho_n)
else:
    unlabeled_set, labeled_set = dataset.datasets_initialization(
        x_all, y_all, init_size, init_weight, pho_p, pho_n)


if moons:
    x_test, y_test = datasets.make_moons(n, noise=0.07)
else:
    x_test, y_test = datasets.make_circles(n, noise=0.03)
y_test = (y_test*2-1).reshape(-1, 1)

test_set = torch.utils.data.TensorDataset(
    torch.from_numpy(x_test).float(), torch.from_numpy(y_test).float())


fig, ax = plt.subplots()

plt.ion()
plt.show()

negative_samples = x_all[y_all.reshape(-1) == 1]
positive_samples = x_all[y_all.reshape(-1) == -1]

px, py = np.array(positive_samples).T
nx, ny = np.array(negative_samples).T
plt.scatter(px, py, color='mistyrose', s=3)
plt.scatter(nx, ny, color='turquoise', s=3)
plt.pause(0.05)

x_init = labeled_set.data_tensor.numpy()
y_init = torch.sign(labeled_set.target_tensor).numpy().reshape(-1)
y_clean = labeled_set.label_tensor.numpy().reshape(-1)

cx, cy = np.array(x_init).T
plt.scatter(cx, cy, s=10, color='yellow')
cx, cy = x_init[y_init == -1].T
plt.scatter(cx, cy, s=40, c='black', alpha=0.2, marker='+')
plt.pause(0.05)


cls = create_new_classifier()
cm = plt.get_cmap('gist_rainbow')

cont = None


def give_correct(y_corrupted, y_clean, k):
    s = y_corrupted + y_clean
    diff_indices = np.argwhere(s == 0).reshape(-1)
    k = min(k, len(diff_indices))
    if k != 0:
        flipped_indices = np.random.choice(diff_indices, k, replace=False)
        y_corrupted[flipped_indices] = y_clean[flipped_indices]
        return flipped_indices
    return None


for corr in range(corr_times):

    print('\nRelabel {}'.format(corr))

    cls.train(labeled_set, test_set, retrain_epochs,
              convex_epochs, test_interval=10,
              print_interval=3000, test_on_train=True)
    if corr >= 1:
        cont.collections[0].set_linewidth(1)
        cont.collections[0].set_alpha(0.3)
    cont = cls.model.plot_boundary(ax, colors=[cm(corr/corr_times)])
    plt.pause(0.05)

    relabel_idxs, drop_idxs = HeuristicRelabel().diverse_flipped(
        labeled_set, 1, corr_size, 5, pho_p, pho_n)
    relabel_idxs, _ = relabel_idxs[0]

    print(relabel_idxs)
    labeled_set.query(relabel_idxs)
    labeled_set.remove_no_effect()

    x_dropped = x_init[drop_idxs]
    dx, dy = x_dropped.T
    plt.scatter(dx, dy, s=40, marker='x', label='{} dropped'.format(corr))
    plt.legend()
    plt.pause(0.05)

    x_selected = x_init[relabel_idxs]
    y = torch.sign(labeled_set.target_tensor).numpy().reshape(-1)
    # print(labeled_set.target_tensor.numpy().reshape(-1)[relabel_idxs])
    y_selected = y[relabel_idxs]

    sx, sy = x_selected.T
    plt.scatter(sx, sy, s=20, alpha=0.6, label='{}'.format(corr))
    sx, sy = x_selected[y_selected == -1].T
    plt.scatter(sx, sy, s=50, c='black', alpha=0.2, marker='+')
    plt.legend()
    plt.pause(0.05)

    while not plt.waitforbuttonpress(1):
        pass

plt.figure()
plt.plot(cls.train_accuracies, label='train accuracy')
plt.plot(cls.test_accuracies, label='test accuracy')
# plt.plot(cls.high_loss_fractions, label='fraction of high loss samples')
plt.plot(cls.critic_confs, label='critic conf')
plt.legend()

while not plt.waitforbuttonpress(1):
    pass
