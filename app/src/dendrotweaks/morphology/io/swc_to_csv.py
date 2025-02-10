import pandas as pd

SWC_SPECIFICATION = {
    0: 'undefined',
    1: 'soma',
    2: 'axon',
    3: 'dend',
    4: 'apic',
    5: 'custom',
    6: 'neurite',
    7: 'glia',
}

def swc_to_csv(path_to_swc_file: str, path_to_csv_file: str, specification=None):
    """
    Convert an SWC file to a CSV file.
    """
    with open(path_to_swc_file, 'r') as f:
        lines = f.readlines()
    lines = [' '.join(line.split()) for line in lines if line.strip()]
    with open(path_to_swc_file, 'w') as f:
        f.write('\n'.join(lines))

    df = pd.read_csv(
        path_to_swc_file, 
        sep=' ', 
        header=None, 
        comment='#', 
        names=['Index', 'Type', 'X', 'Y', 'Z', 'R', 'Parent'],
        index_col=False
    )

    if (df['R'] == 0).all():
        df['R'] = 1.0

    if df['Index'].duplicated().any():
        raise ValueError("The SWC file contains duplicate node ids.")

    specification = SWC_SPECIFICATION.update(specification or {})

    unique_types = df['Type'].unique()
    missing_types = set(unique_types) - set(specification.keys())

    for t in missing_types:
        specification[t] = f'custom_{t}'

    df['Type'] = df['Type'].map(lambda x: specification.get(x, f'custom_{x}'))

    df.to_csv(path_to_csv_file, index=False)