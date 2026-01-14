import numpy as np
import math
import pandas as pd
import sys
from multi_knapsack_solver import bin_solver_main
import copy


pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def moment_of_inertia(odiam, idiam):
    return math.pi * (math.pow(odiam, 4) - math.pow(idiam, 4)) / 64


def area(odiam, idiam):
    return math.pi * (math.pow(odiam, 2) - math.pow(idiam, 2)) / 4


def kappa(elasticity, moi, area, density):
    # return math.sqrt((elasticity * moi * gravity) / (area * density))
    return math.sqrt((elasticity * moi) / (area * density))


def pipe_length(freq, elasticity, density, odiam, idiam):
    inertia_val = moment_of_inertia(odiam, idiam)
    area_val = area(odiam, idiam)
    kappa_val = kappa(elasticity, inertia_val, area_val, density)
    # return math.sqrt(7145.7 * kappa_val / (2 * math.pi * freq))
    return math.sqrt(22.373 * kappa_val / (2 * math.pi * freq)) * 10000  # to put in 0.1mm


def compare_freq(elasticity, density, odiam, idiam, inches=True):
    length = 1  # in m
    if inches:
        gravity = 386.4
        length = 39.3701
    else:
        gravity = 1
    lambd = 22.373

    inertia_val = moment_of_inertia(odiam, idiam)
    area_val = area(odiam, idiam)
    freq = lambd / (2 * math.pi) * math.sqrt(
        (elasticity * inertia_val * gravity) / (area_val * density * math.pow(length, 4)))
    return freq


def get_chime_ranges(note_list):
    total_note_list = []
    note_list_rhs = []
    increment = 0
    while True:
        new_note_list = [(i[:-1] + str(int(i[-1]) + increment)) for i in note_list]
        total_note_list.append(new_note_list)
        increment += 1
        if int(new_note_list[-1][-1]) >= 9:
            increment = 1
            break
    while True:
        new_note_list = [(i[:-1] + str(int(i[-1]) - increment)) for i in note_list]
        note_list_rhs.append(new_note_list)
        increment += 1
        if int(new_note_list[0][-1]) <= 1:
            break

    total_note_list = note_list_rhs[::-1] + total_note_list

    return total_note_list


def extract_notes(note_list, note_df):  # TODO add some tests and stuff
    freq_list = []
    for note in note_list:
        assert len(note) == 2 or len(note) == 7 or len(note) == 6, "Incorrect note input"
        # the above kinda hacky maybe make better one in future or do checks earlier on

        octave = note[-1]
        key = note[:-1]

        # maybe assert some stuff here about number and letter, but tbh should be handled before if splitting like this

        # sort out if sharp or flat, this is so bad but eh
        if len(key) != 1:
            letter = key[:1]
            sorf = key[1:]
            if sorf == "sharp":
                if letter == "G":
                    key += ",Aflat"
                else:
                    new_letter = chr(ord(letter) + 1)
                    key += "," + new_letter + "flat"
            elif sorf == "flat":
                if letter == "A":
                    key = "Gsharp," + key
                else:
                    new_letter = chr(ord(letter) - 1)
                    key = new_letter + "sharp," + key
            else:
                print("Messedup")
                sys.exit(0)

        freq = note_df[octave].loc[key]
        freq_list.append(freq)

        # should assert some stuff

    return freq_list


def extract_chime_lengths(freq_list, elasticity, density, odiam, idiam):
    chime_length_list = []
    for freq in freq_list:
        chime_length = pipe_length(freq, elasticity, density, odiam, idiam)
        chime_length_list.append(chime_length)

    return chime_length_list


def calc_pipes(notes, pipe_lengths, odiam, idiam, material="Aluminium", cutting_allowance: int = 2, optim="Exact"):
    # TODO be aware of scaling just to be sure it all matches
    """
    :param notes:
    :param pipe_lengths: list in m
    :param odiam: in mm
    :param idiam: in mm
    :param material: pipe material
    :param cutting_allowance: in mm
    :param optim: Exact, Lowest, Highest, finds the highest or lowest or the exact specified notes
    :return:
    """
    scalar = 10000
    odiam /= 1000
    idiam /= 1000
    pipe_lengths_adj = [scalar * i for i in pipe_lengths]  # convert to 0.1mm for int programming

    elasticity = 68947573000  # TODO improve material allocation part
    density = 2712.6307

    # i choose notes needed, assert this is an even number I think or maybe allow it to repeat first one if pentatonic
    assert len(notes) % 2 == 0, "Odd number of notes selected, please use even value"

    notes_df = pd.read_csv("440hz_notes.csv", index_col=0)

    # get range of possible octave values function
    chime_range_options = get_chime_ranges(notes)

    def loop_inner(chime_notes):
        freq_list = extract_notes(chime_notes, notes_df)
        chime_length_list = extract_chime_lengths(freq_list, elasticity, density, odiam, idiam)  # in mm
        chime_length_list = [i + (cutting_allowance * 10) for i in chime_length_list]  # adds cutting tolerance
        bin_fit = bin_solver_main(chime_length_list, pipe_lengths_adj, chime_notes, scalar)
        # TODO do we want to remove cutting allowance after or nah?

        return bin_fit

    # then for loop over it here for lowest
    if optim == "Lowest":
        for chime_range in chime_range_options:
            pipe_fit = loop_inner(chime_range)
            if len(pipe_fit) != 0:
                break
    elif optim == "Highest":  # TODO check this works
        for chime_range in chime_range_options[::-1]:
            pipe_fit = loop_inner(chime_range)
            if len(pipe_fit) != 0:
                break
    elif optim == "Exact":
        pipe_fit = loop_inner(notes)
    else:
        print("Incorrect Optim Choice")
        sys.exit(0)

    if len(pipe_fit) == 0:
        print("There is not enough pipe material for this selection.")
        sys.exit(0)

    return pd.DataFrame(pipe_fit)


odiam = 48
idiam = 40
note_list = ["Csharp3", "D3", "E3", "F3", "G3", "C4", "C5", "C6"]
pipe_length_list = [2.1, 5.2, 2.4, 9]
print(calc_pipes(note_list, pipe_length_list, odiam, idiam, optim="Exact"))
