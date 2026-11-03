"""Sample 800 training and 200 test rows from the supplied placement files."""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

FEATURES = ['CGPA', 'Internships', 'Projects', 'Coding_Skills',
            'Communication_Skills', 'Aptitude_Test_Score', 'Certifications', 'Backlogs']
TARGET = 'Placement_Status'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--test', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    train, test = pd.read_csv(args.train), pd.read_csv(args.test)
    for name, data in [('train', train), ('test', test)]:
        if not set(FEATURES + [TARGET, 'Student_ID']).issubset(data.columns):
            raise ValueError(f'{name} is missing columns')
        if (data.groupby(FEATURES, dropna=False)[TARGET].nunique() > 1).any():
            raise ValueError(f'{name} has conflicting labels for identical features')
    test = test.drop_duplicates(FEATURES)
    _, test_sample = train_test_split(test, test_size=200, random_state=42, stratify=test[TARGET])
    keys = test_sample[FEATURES].assign(_in_test=True)
    train = train.merge(keys, on=FEATURES, how='left', validate='many_to_one')
    train = train.loc[train['_in_test'].isna()].drop(columns=['_in_test']).drop_duplicates(FEATURES)
    train = train.loc[~train['Student_ID'].isin(test_sample['Student_ID'])]
    _, train_sample = train_test_split(train, test_size=800, random_state=42, stratify=train[TARGET])
    args.out.mkdir(parents=True, exist_ok=True)
    train_sample.to_csv(args.out / 'train_800.csv', index=False)
    test_sample.to_csv(args.out / 'test_200.csv', index=False)
    print('Training rows:', len(train_sample), 'Test rows:', len(test_sample))
    print('Train class counts:', train_sample[TARGET].value_counts().to_dict())
    print('Test class counts:', test_sample[TARGET].value_counts().to_dict())


if __name__ == '__main__':
    main()
