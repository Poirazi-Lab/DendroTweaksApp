
def number_of_sections(n_terminals: int) -> int:
    """Calculates the number of segments based on Uylings and Pelt, 2002."""
    return 2*n_terminals - 1

def number_of_bifurcations(n_terminals: int) -> int:
    """Calculates the number of bifurcations based on Uylings and Pelt, 2002."""
    return n_terminals - 1


def neurite_path_lengths(neurite) -> float:
    """Calculates the path length of a neurite."""
    return [sec.path_length(1) for sec in neurite.terminals]
    
def neurite_radial_distances(neurite) -> float:
    """Calculates the radial distance of a neurite."""
    root = neurite.root
    return [radial_distance(root, sec) for sec in neurite.terminals]



def measure_topology(sec_tree):

    soma = sec_tree.soma
    neurite_roots = soma.children
    for root in neurite_roots:
        measure_neurite_topology(root)
    


def measure_neurite_topology(root):
    neurite_sections = root.subtree
    
    return {
        "domains": set([sec.domain for sec in neurite_sections]),
        "number_of_sections": len(neurite_sections),
        "number_of_bifurcations": sum(1 for sec in neurite_sections if len(sec.children) == 2),
        "number_of_terminations": sum(1 for sec in neurite_sections if len(sec.children) == 0),
        "symmetry": sum(1 for sec in neurite_sections if len(sec.children) == 2) / len(neurite_sections),
        "max_branch_order": max([sec.depth for sec in neurite_sections]),
    }


def measure_neutire_geometry(root):
    neurite_sections = root.subtree

    return {
        "total_length": sum([sec.L for sec in neurite_sections]),
        "total_surface_area": sum([sec.area() for sec in neurite_sections]),
        # "total_volume": sum([sec.volume() for sec in neurite_sections]),
        "average_diameter": np.mean([sec.diam for sec in neurite_sections]),
        "average_section_length": np.mean([sec.L for sec in neurite_sections]),
        "average_section_surface_area": np.mean([sec.area() for sec in neurite_sections]),
        # "average_section_volume": np.mean([sec.volume() for sec in neurite_sections])
    }


def measure_soma_geometry(soma):
    return {
        "diameter": soma.diam,
        "surface_area": soma.area(),
        # "volume": soma.volume()
    }   



def measure_geometry(sec_tree):
    diams = [seg.diam for seg in self.model.selected_segs]
    lengths = [sec.L for sec in self.model.selected_secs]
    areas = [seg.area() for seg in self.model.selected_segs]
    stats = {
        "N_soma_children": len(self.model.cell.soma[0].children()),
        "N_sections": len(self.model.selected_secs),
        "N_segments": len(self.model.selected_segs),
        "N_bifurcations": sum([1 for sec in self.model.selected_secs if len(sec.children()) == 2]),
        "average_diam": (np.round(np.mean(diams), 2), np.round(np.std(diams), 2)),
        "average_length": (np.round(np.mean(lengths), 2), np.round(np.std(lengths), 2)),
        "average_area": (np.round(np.mean(areas), 2), np.round(np.std(areas), 2)),
        "total_length": np.round(np.sum(lengths), 2),
        "total_area": np.round(np.sum(areas), 2)
    }
    return stats

def update_histogram(self):
    areas = [seg.area() for seg in self.model.selected_segs]
    hist, edges = np.histogram(areas, bins='auto')
    return hist, edges