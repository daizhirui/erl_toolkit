import argparse
import matplotlib.pyplot as plt
import pandas as pd


def draw_curves(csv_file, y_label=None, title=None):
    df = pd.read_csv(csv_file)
    columns = df.columns.tolist()
    if len(columns) < 2:
        raise ValueError("CSV file must contain at least two columns for x and y values.")
    x = df[columns[0]].to_numpy()
    for i in range(1, len(columns)):
        y = df[columns[i]].to_numpy()
        plt.plot(x, y, label=columns[i])
    plt.xlabel(columns[0])
    if y_label is not None:
        plt.ylabel(y_label)
    else:
        plt.ylabel("Values")
    if title is not None:
        plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Draw curves based the given CSV file.")
    parser.add_argument("csv_file", type=str, help="Path to the CSV file containing curve data.")
    parser.add_argument("--y_label", type=str, default=None, help="Label for the y-axis.")
    parser.add_argument("--title", type=str, default=None, help="Title of the plot.")
    args = parser.parse_args()
    csv_file = args.csv_file

    # Call the function to draw curves with the provided CSV file
    draw_curves(csv_file, y_label=args.y_label, title=args.title)


if __name__ == "__main__":
    main()
