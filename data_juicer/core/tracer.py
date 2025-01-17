import os

import pandas as pd
from datasets import Dataset
from loguru import logger
from data_juicer.utils.constant import DEFAULT_PREFIX, Fields
import json
from multiprocessing import Pool
import jsonlines

class Tracer:
    """
    The tracer to trace the sample changes before and after an operator
    process.

    The comparison results will be stored in the work directory.
    """

    def __init__(self, work_dir, show_num=10):
        """
        Initialization method.

        :param work_dir: the work directory to store the comparison
            results
        :param show_num: the maximum number of samples to show in the
            comparison result files.
        """
        self.work_dir = os.path.join(work_dir, 'trace')
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir)
        self.show_num = show_num

    def trace_mapper(self, op_name: str, previous_ds: Dataset,
                     processed_ds: Dataset, text_key: str):
        """
        Compare datasets before and after a Mapper.

        This will mainly show the different sample pairs due to the
        modification by the Mapper

        :param op_name: the op name of mapper
        :param previous_ds: dataset before the mapper process
        :param processed_ds: dataset processed by the mapper
        :param text_key: which text_key to trace
        :return:
        """
        assert len(previous_ds) == len(processed_ds)
        dif_dict = []
        num = 0

        # Find different samples orderly between previous and processed
        # datasets until the total number of found sample pairs is enough.
        for i in range(len(previous_ds)):
            previous_sample = previous_ds[i][text_key]
            processed_sample = processed_ds[i][text_key]
            if previous_sample != processed_sample:
                dif_dict.append({
                    'original text': previous_sample,
                    'processed_text': processed_sample,
                })
                num += 1
                if num >= self.show_num:
                    break

        if len(dif_dict) == 0:
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return
        elif len(dif_dict) < self.show_num:
            logger.warning(f'There are {len(dif_dict)} different samples '
                           f'before and after op [{op_name}] -- less than '
                           f'expected {self.show_num} samples.')

        # export the tracer results.
        res_name = f'mapper-{op_name}.jsonl'
        # dif_df = pd.DataFrame(dif_dict)
        # dif_df.to_json(os.path.join(self.work_dir, res_name),
        #                orient='records',
        #                lines=True,
        #                force_ascii=False)
        with jsonlines.open(os.path.join(self.work_dir, res_name), mode='w') as writer:
            writer.write_all(dif_dict)
            
            
    def trace_batch_mapper(self, op_name: str, previous_ds: Dataset,
                           processed_ds: Dataset, text_key: str):
        """
        Compare datasets before and after a BatchMapper.

        This will mainly show the new samples augmented by the BatchMapper

        :param op_name: the op name of mapper
        :param previous_ds: dataset before the mapper process
        :param processed_ds: dataset processed by the mapper
        :param text_key: which text_key to trace
        :return:
        """
        assert previous_ds[0][text_key] == processed_ds[0][text_key]
        aug_dict = []

        # Get the first samples
        for i in range(len(processed_ds)):
            processed_sample = processed_ds[i]
            aug_dict.append(processed_sample)
            if i + 1 >= self.show_num:
                break

        if len(aug_dict) == 0:
            logger.warning(f'Datasets before and after op [{op_name}] are '
                           f'empty. Thus no comparison results would be '
                           f'generated.')
            return
        elif len(aug_dict) < self.show_num:
            logger.warning(f'There are only {len(aug_dict)} samples -- less '
                           f'than expected {self.show_num} samples.')

        # export the tracer results.
        res_name = f'mapper-{op_name}.jsonl'
        # dif_df = pd.DataFrame(aug_dict)
        # dif_df.to_json(os.path.join(self.work_dir, res_name),
        #                orient='records',
        #                lines=True,
        #                force_ascii=False)
        
        
        with jsonlines.open(os.path.join(self.work_dir, res_name), mode='w') as writer:
            writer.write_all(aug_dict)

    def trace_filter(self, op_name: str, previous_ds: Dataset,
                     processed_ds: Dataset):
        """
        Compare datasets before and after a Filter.

        This will mainly show the filtered samples by the Filter

        :param op_name: the op name of filter
        :param previous_ds: dataset before the filter process
        :param processed_ds: dataset processed by the filter
        :return:
        """
        if len(previous_ds) == len(processed_ds):
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return

        # get the number of filtered samples.
        total_dif_num = len(previous_ds) - len(processed_ds)
        # index of the current sample in the previous dataset
        i = 0
        filter_dict = []
        # number of found filtered samples. It's the offset bewteen two
        # datasets as well.
        num = 0
        while i < len(previous_ds):
            if i - num >= len(processed_ds) or \
                    previous_ds[i] != processed_ds[i - num]:
                # 1. If all samples in processed dataset are checked but there
                # still some samples left in the previous dataset, all of these
                # left samples are filtered.
                # 2. If the corresponding samples in previous and processed
                # datasets are different, samples in the previous dataset are
                # filtered.
                num += 1
                filter_dict.append(previous_ds[i])
            if num >= self.show_num or num >= total_dif_num:
                # If the total number of found filtered samples is enough or we
                # have found all filtered samples, just stop.
                break
            i += 1
        if len(filter_dict) == 0:
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return
        elif len(filter_dict) < self.show_num:
            logger.warning(f'There are {len(filter_dict)} filtered samples '
                           f'before and after op [{op_name}] -- less than '
                           f'expected {self.show_num} samples.')

        # export the tracer results.
        res_name = f'filter-{op_name}.jsonl'
        # filter_df = pd.DataFrame(filter_dict)
        # filter_df.to_json(os.path.join(self.work_dir, res_name),
        #                   orient='records',
        #                   lines=True,
        #                   force_ascii=False)
        
        with jsonlines.open(os.path.join(self.work_dir, res_name), mode='w') as writer:
            writer.write_all(filter_dict)

    def trace_deduplicator(self, op_name: str, dup_pairs: list):
        """
        Compare datasets before and after a Deduplicator.

        This will mainly show the near-duplicate sample pairs extracted
        by the Deduplicator. Different from the other two trace methods,
        the trace process for deduplicator is embedded into the process
        method of deduplicator, but the other two trace methods are
        independent of the process method of mapper and filter operators

        :param op_name: the op name of deduplicator
        :param dup_pairs: duplicate sample pairs obtained from
            deduplicator
        :return:
        """
        if dup_pairs is None:
            logger.warning(f'Op [{op_name}] does not generate dup_pairs '
                           f'correctly, thus no comparison results can be '
                           f'obtained from this op.')
            return
        if len(dup_pairs) == 0:
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return
        elif len(dup_pairs) < self.show_num:
            logger.warning(f'There are {len(dup_pairs)} filtered samples '
                           f'before and after op [{op_name}] -- less than '
                           f'expected {self.show_num} samples.')

        # reorganize the duplicate pairs
        dup_dict = []
        for i, key in enumerate(dup_pairs):
            dup_dict.append({
                'dup_num': len(dup_pairs[key]) - 1,
                'ori': dup_pairs[key][0],
            })
            for j, item in enumerate(dup_pairs[key][1:]): 
                dup_dict[i]['dup%d' % (j + 1)] = item

        # export the tracer result.
        res_name = f'duplicate-{op_name}.jsonl'
        # dup_df = pd.DataFrame(dup_dict)
        # dup_df.to_json(os.path.join(self.work_dir, res_name),
        #                orient='records',
        #                lines=True,
        #                force_ascii=False)
    
        with jsonlines.open(os.path.join(self.work_dir, res_name), mode='w') as writer:
            writer.write_all(dup_dict)

        # placeholder = 'N/A'
        # df_filled = dup_df.applymap(lambda x: placeholder if pd.isnull(x) else x)
        # with open(os.path.join(self.work_dir, res_name), 'w') as f:
        #     for index, row in df_filled.iterrows():
        #         json_line = {key: value for key, value in row.items() if value != placeholder}
        #         f.write(json.dumps(json_line) + '\n') 
        
        
    def trace_mycleanlab(self, op_name: str, previous_ds: Dataset,
                     processed_ds: Dataset):
        """
        Compare datasets before and after a Filter.

        This will mainly show the filtered samples by the Filter

        :param op_name: the op name of filter
        :param previous_ds: dataset before the filter process
        :param processed_ds: dataset processed by the filter
        :return:
        """
        
        issues = ["is_odd_aspect_ratio_issue", 
                  "is_low_information_issue", "is_light_issue", 
                  "is_grayscale_issue", "is_dark_issue", "is_blurry_issue"]
        
        if len(previous_ds) == len(processed_ds):
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return

        # get the number of filtered samples.
        total_dif_num = len(previous_ds) - len(processed_ds)
        # index of the current sample in the previous dataset
        i = 0
        filter_dict = []
        # number of found filtered samples. It's the offset bewteen two
        # datasets as well.
        num = 0
        while i < len(previous_ds):
            if i - num >= len(processed_ds) or \
                    previous_ds[i] != processed_ds[i - num]:
                # 1. If all samples in processed dataset are checked but there
                # still some samples left in the previous dataset, all of these
                # left samples are filtered.
                # 2. If the corresponding samples in previous and processed
                # datasets are different, samples in the previous dataset are
                # filtered.
                num += 1
                filter_dict.append(previous_ds[i])
            if num >= self.show_num or num >= total_dif_num:
                # If the total number of found filtered samples is enough or we
                # have found all filtered samples, just stop.
                break
            i += 1
        if len(filter_dict) == 0:
            logger.warning(f'Datasets before and after op [{op_name}] are all '
                           f'the same. Thus no comparison results would be '
                           f'generated.')
            return
        elif len(filter_dict) < self.show_num:
            logger.warning(f'There are {len(filter_dict)} filtered samples '
                           f'before and after op [{op_name}] -- less than '
                           f'expected {self.show_num} samples.')

        # export the tracer results.
        res_name = f'filter-{op_name}.jsonl'
        # filter_df = pd.DataFrame(filter_dict)
        with jsonlines.open(os.path.join(self.work_dir, res_name), mode='w') as writer:
            writer.write_all(filter_dict)
        # filter_df.to_json(os.path.join(self.work_dir, res_name),
        #                   orient='records',
        #                   lines=True,
        #                   force_ascii=False)
        
        # for issue in issues:
        #     stats_array = np.array([d['stats'] for d in filter_df])
        #     tmp_df = [d for d in filter_df if any(stats_array[filter_df.index(d), filter_df[0].keys().index(DEFAULT_PREFIX + issue)])]
        #     # tmp_df = filter_df[pd.DataFrame(filter_df[Fields.stats].tolist())[DEFAULT_PREFIX + issue].apply(lambda x: True in x)]
        #     if tmp_df:
        #         # tmp_df.to_json(os.path.join(self.work_dir, f'cleanvision-{issue}.jsonl'),
        #         #             orient='records',
        #         #             lines=True,
        #         #             force_ascii=False)
        #         with jsonlines.open(os.path.join(self.work_dir, f'cleanvision-{issue}.jsonl', mode='w') as writer:
        #             writer.write_all(filter_dict)