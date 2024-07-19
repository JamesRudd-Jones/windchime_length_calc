from ortools.linear_solver import pywraplp
import sys
import math


# TODO ref this source for the solver


def create_data_model(chime_lengths, pipe_lengths, notes):
    """Create the data for the example."""
    data = {}
    weights = [round(i) for i in chime_lengths]
    data["weights"] = weights
    data["items"] = list(range(len(weights)))
    data["item_name"] = notes

    data["bin_capacities"] = pipe_lengths
    data["num_bins"] = len(data["bin_capacities"])
    data["bins"] = range(data["num_bins"])

    return data


def bin_solver_main(chime_lengths, pipe_lengths, notes, scalar):
    data = create_data_model(chime_lengths, pipe_lengths, notes)

    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver("SCIP")

    if not solver:
        return

    # Variables
    # x[i, j] = 1 if item i is packed in bin j.
    x = {}
    for i in data["items"]:
        for j in data["bins"]:
            x[(i, j)] = solver.IntVar(0, 1, "x_%i_%i" % (i, j))

    # y[j] = 1 if bin j is used.
    y = {}
    for j in data["bins"]:
        y[j] = solver.IntVar(0, 1, "y[%i]" % j)

    # Constraints
    # Each item must be in exactly one bin.
    for i in data["items"]:
        solver.Add(sum(x[i, j] for j in data["bins"]) == 1)

    # The amount packed in each bin cannot exceed its capacity.
    for j in data["bins"]:
        solver.Add(
            sum(x[(i, j)] * data["weights"][i] for i in data["items"])
            <= y[j] * data["bin_capacities"][j]
        )

    # Objective: minimize the number of bins used.
    solver.Minimize(solver.Sum([y[j] for j in data["bins"]]))

    status = solver.Solve()

    total_list = {}
    if status == pywraplp.Solver.OPTIMAL:
        num_bins = 0
        for j in data["bins"]:
            if y[j].solution_value() == 1:
                bin_items = []
                bin_items_lengths = []
                hole_height = []
                bin_weight = 0
                for i in data["items"]:
                    if x[i, j].solution_value() > 0:
                        bin_items.append(data["item_name"][i])
                        bin_items_lengths.append(round(data["weights"][i] / scalar, 4))
                        hole_height.append(round(data["weights"][i] * 0.2242 / scalar, 4))
                        bin_weight += data["weights"][i]
                if bin_items:
                    num_bins += 1
                cutting_fit = {"Notes": (bin_items,),
                               "Chime Lengths (m)": (bin_items_lengths,),
                               "Hole Placement (m)": (hole_height,),
                               "Total Chime Length (m)": bin_weight / scalar}
                total_list[f"Pipe {j} Length : {data["bin_capacities"][j] / scalar}m"] = cutting_fit

    return total_list
