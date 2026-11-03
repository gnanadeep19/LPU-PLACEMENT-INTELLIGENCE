import os
import glob
import pandas as pd

def inspect_all_datasets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(base_dir, "*.csv")))
    
    print("=" * 80)
    print(f"LPU PLACEMENT INTELLIGENCE PLATFORM - DATASET REPOSITORY INSPECTION")
    print(f"Total Datasets Found: {len(files)}")
    print("=" * 80)
    
    total_records = 0
    
    for i, file_path in enumerate(files, 1):
        filename = os.path.basename(file_path)
        df = pd.read_csv(file_path)
        total_records += len(df)
        
        print(f"\n[{i}] {filename}")
        print(f"    Total Records (Rows): {len(df):,}")
        print(f"    Features (Columns)  : {len(df.columns)}")
        print(f"    Columns             : {list(df.columns)}")
        print(f"    Sample Row (1st)    : {df.iloc[0].to_dict()}")
        
    print("\n" + "=" * 80)
    print(f"SUMMARY: {len(files)} CSV Datasets | {total_records:,} Total Student Records")
    print("=" * 80)

if __name__ == "__main__":
    inspect_all_datasets()
