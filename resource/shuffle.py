import pandas as pd
import numpy as np

def shuffle_excel_rows(input_file, output_file, seed=42):
    """
    Shuffle rows in an Excel file and save to a new file.
    
    Parameters:
    input_file (str): Path to input Excel file
    output_file (str): Path to save shuffled Excel file
    seed (int): Random seed for reproducibility
    """
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Read the Excel file
    df = pd.read_excel(input_file)
    
    # Shuffle the rows
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    
    # Save to new Excel file
    df_shuffled.to_excel(output_file, index=False)
    
    print(f"Shuffled data saved to {output_file}")
    print(f"Original row count: {len(df)}")
    print(f"Shuffled row count: {len(df_shuffled)}")

# Example usage
input_file = "Test 01.xlsx"
output_file = "Shuffled Test 01.xlsx"
shuffle_excel_rows(input_file, output_file, seed=42)