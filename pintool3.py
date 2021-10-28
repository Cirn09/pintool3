import re
import os
from os import path
from pathlib import Path
import sys
import math
import signal
import string
import subprocess
import argparse
import configparser
from multiprocessing import Pool

config = configparser.ConfigParser()
default_config = '''[path]
pin = PATH_TO_PIN
bcount32 = PATH_TO_BCOUNT32
bcount64 = PATH_TO_BCOUNT64
'''
config_path_dir = path.join(Path.home(), '.config')
config_path = path.join(config_path_dir, 'pintool3.conf')
if not path.exists(config_path_dir):
    os.mkdir(config_path_dir)
if not path.exists(config_path):
    with open(config_path, 'w') as f:
        config.read_string(default_config)
        config.write(f)
    print(f'Please complete the config file({config_path})')
    exit(-1)
config.read(config_path)

r = re.compile(r"Count ([\w]+)")


def pin(cmd: list,
        input: str,
        arch: int,
        range_start: int = 0,
        range_end: int = 0,
        count_on_branch_taken: bool = False,
        module: str = '',
        retry: int = 0,
        encoding: str = 'utf8') -> int:
    '''`cmd < input` -> branch count'''
    if isinstance(cmd, str):
        _cmd = f'"{config["path"]["pin"]}"'
        if arch == 32:
            _cmd += f' -t "{config["path"]["bcount32"]}"'
        elif arch == 64:
            _cmd += f' -t "{config["path"]["bcount64"]}"'
        else:
            print('unknow Arch')
            exit(-1)
        if range_start:
            _cmd += f' -s {range_start}'
        if range_end:
            _cmd += f' -e {range_end}'
        if count_on_branch_taken:
            _cmd += ' -b'
        if module:
            _cmd += f' -p "{module}"'
        _cmd += f' -- {cmd}'
    elif isinstance(cmd, list):
        _cmd = [config["path"]["pin"]]

        if arch == 32:
            _cmd += ['-t', config["path"]["bcount32"]]
        elif arch == 64:
            _cmd += ['-t', config["path"]["bcount64"]]
        else:
            print('unknow Arch')
            exit(-1)
        if range_start:
            _cmd += ['-s', str(range_start)]
        if range_end:
            _cmd += ['-e', str(range_end)]
        if count_on_branch_taken:
            _cmd += ['-b']
        if module:
            _cmd += ['-p', module]
        _cmd += ['--'] + cmd
    input_encode = bytes(input + '\n', encoding)

    retry_time = 0
    while True:
        try:
            p = subprocess.run(
                _cmd,
                #    shell=True,
                check=True,
                input=input_encode,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            info = str(p.stderr, encoding)
            if t := re.search(r, info):
                count = t.groups()[0]
                return int(count)
            else:
                print(f'stderr: {info}')
                print('regex ("Count ([\\w]+)) not found in stderr')
                exit(-1)
        except subprocess.CalledProcessError as e:
            if retry_time < retry:
                retry_time += 1
                continue
            else:
                raise e


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def multipin(cmd: list,
             inputs: list,
             arch: int,
             range_start: int = 0,
             range_end: int = 0,
             count_on_branch_taken: bool = False,
             module: str = '',
             retry: int = 0,
             encoding: str = 'utf8'):
    '`cmd < [input0, input1 ...]` -> [count0, count1 ...]'
    pool = Pool(initializer=init_worker)
    try:
        r = []
        for input in inputs:
            m = pool.apply_async(
                pin, (cmd, input, arch, range_start, range_end,
                      count_on_branch_taken, module, retry, encoding))
            r.append(m)
        pool.close()
        return [x.get() for x in r]
    except KeyboardInterrupt:
        print('break, waiting for subprocesses...')
        # pool.terminate()
        # doc for Pool.terminate():
        # > Note that descendant processes of the process will *not* be terminated – they will simply become orphaned.
        pool.join()
        exit()


def solve_single(cmd: list,
                 inputs: list,
                 arch: int,
                 type: str = 'max',
                 range_start: int = 0,
                 range_end: int = 0,
                 count_on_branch_taken: bool = False,
                 module: str = '',
                 retry: int = 0,
                 encoding: str = 'utf8'):
    if type == 'max':
        func = max
        target_count = -1
    elif type == 'min':
        func = min
        target_count = math.inf
    else:
        func = None
    target_index = None

    max_input_len = max(map(len, inputs))

    for index, input in enumerate(inputs):
        count = pin(cmd, input, arch, range_start, range_end,
                    count_on_branch_taken, module, retry, encoding)
        t = func(target_count, count)
        if t != target_count:
            target_index = index
            target_count = t
            s = '* '
        else:
            s = '  '
        s += input.ljust(max_input_len, ' ')
        s += ' | ' + str(count)
        print(s)
    s = '> ' + inputs[target_index].ljust(max_input_len,
                                          ' ') + ' | ' + str(target_count)
    print(s)

    return target_index


def solve_multi(cmd: list,
                inputs: list,
                arch: int,
                type: str = 'max',
                range_start: int = 0,
                range_end: int = 0,
                count_on_branch_taken: bool = False,
                module: str = '',
                retry: int = 0,
                encoding: str = 'utf8'):
    counts = multipin(cmd, inputs, arch, range_start, range_end,
                      count_on_branch_taken, module, retry, encoding)
    if type == 'max':
        func = max
    elif type == 'min':
        func = min
    else:
        func = None

    target_index = func(range(len(counts)), key=lambda x: counts[x])
    if len(set(counts)) == 1:
        target_index = -1

    max_input_len = max(map(len, inputs))
    max_count_len = max(map(lambda x: math.ceil(math.log10(x)), counts))
    for i in range(len(counts)):
        count = counts[i]
        input = inputs[i]

        s = ''
        if i == target_index:
            s += '* '
        else:
            s += '  '
        s += input.ljust(max_input_len, ' ')
        s += ' | ' + str(count).rjust(max_count_len, ' ')
        print(s)
    s = '> ' + inputs[target_index].ljust(max_input_len, ' ') + ' | ' + str(
        counts[target_index])
    print(s)

    return target_index


def len_detect(cmd: list,
               arch: int,
               multiprocess: bool = True,
               min_length: int = 4,
               max_length: int = 40,
               char: str = '_',
               type: str = 'max',
               range_start: int = 0,
               range_end: int = 0,
               count_on_branch_taken: bool = False,
               module: str = '',
               retry: int = 0,
               encoding: str = 'utf8'):
    if multiprocess:
        solve = solve_multi
    else:
        solve = solve_single
    inputs = [char * len for len in range(min_length, max_length)]
    target = solve(cmd, inputs, arch, type, range_start, range_end,
                   count_on_branch_taken, module, retry, encoding)
    target_len = min_length + target
    print(f'The expected input length may be {target_len}')
    return target_len


def parsearg():
    parser = argparse.ArgumentParser(
        prog='pintool3',
        usage='%(prog)s [options] -- cmd\nexample: %(prog)s -a 64 -- ls -l')
    parser.add_argument(
        '-a',
        '--arch',
        dest='arch',
        type=int,
        required=True,
        help='Program architecture 32 or 64 bits, -a 32 or -a 64')
    parser.add_argument(
        '-m',
        '--module',
        dest='module',
        type=str,
        default='',
        help='Module name to count, -u exam.dll (default *.exe)')
    parser.add_argument('-s',
                        '--range-start',
                        dest='range_start',
                        type=lambda x: int(x, 0),
                        default=0,
                        help='Start *offset* of the record range.')
    parser.add_argument(
        '-e',
        '--range-end',
        dest='range_end',
        type=lambda x: int(x, 0),
        default=0,
        help='End *offset* of the record range. 0 mean module end.')
    parser.add_argument(
        '-b',
        '--count-on-branch-taken',
        dest='count_on_branch_taken',
        action='store_true',
        default=False,
        help='Count all branch or just taken branch. (default: false)')
    parser.add_argument('--disable-multiprocess',
                        dest='disable_multiprocess',
                        action='store_true',
                        default=False,
                        help='Disable multiprocess')
    parser.add_argument('-r',
                        '--retry',
                        dest='retry',
                        type=int,
                        default=0,
                        help='Retry times.')
    parser.add_argument('--encoding',
                        dest='encoding',
                        type=str,
                        default='utf8',
                        help='Input encoding.')
    parser.add_argument('-d',
                        '--detect',
                        dest='detect',
                        action='store_true',
                        default=False,
                        help='Try detech expected input length.')
    parser.add_argument(
        '-c',
        '--charset',
        dest='charset',
        type=str,
        default=
        '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~',
        help=
        'Charset definition for brute force. -c "abc..." (default: string.printable-string.whitespace)'
    )
    parser.add_argument('-p',
                        '--padding',
                        dest='padding',
                        type=str,
                        default='\\',
                        help="padding (default: '\\').")
    parser.add_argument(
        '-l',
        '--length',
        dest='length',
        type=int,
        default=40,
        help='Input length or max input length (when detect on).')
    parser.add_argument('-t',
                        '--type',
                        dest='type',
                        type=str,
                        default='max',
                        help='max or min')
    parser.add_argument(
        '-o',
        '--order',
        dest='order',
        type=str,
        default='normal',
        help='Bruteforce order, "normal", "reverse" or "detect"')
    parser.add_argument('cmd',
                        nargs='+',
                        help='Command line for playing with Pin Tool')

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    args = parser.parse_args()

    return args


if __name__ == "__main__":

    arg = parsearg()
    if arg.detect:
        len_detect(cmd=arg.cmd,
                   arch=arg.arch,
                   multiprocess=not arg.disable_multiprocess,
                   max_length=arg.length,
                   char=arg.padding,
                   type=arg.type,
                   range_start=arg.range_start,
                   range_end=arg.range_end,
                   count_on_branch_taken=arg.count_on_branch_taken,
                   module=arg.module,
                   retry=arg.retry,
                   encoding=arg.encoding)
    else:
        know = {}
        charset = arg.charset
        length = arg.length
        padding = arg.padding
        right_char = ''
        if arg.disable_multiprocess:
            solve = solve_single
        else:
            solve = solve_multi

        if 'detect'.startswith(arg.order):

            def gen_inputs():
                inputs = []

                input_format = ['\x00'] * length
                for key, value in know.items():
                    input_format[key] = value
                input_format = ''.join(input_format)
                for char in charset:
                    inputs.append(input_format.replace('\x00', char))
                return inputs

            def get_index():

                inputs = []
                m = {}
                input_format = ['\x00'] * length
                for key, value in know.items():
                    input_format[key] = value
                input_format = ''.join(input_format)
                for i in range(length):
                    if i not in know:
                        m[len(inputs)] = i
                        input = input_format[0:i] + right_char + input_format[
                            i + 1:]
                        inputs.append(input.replace('\x00', padding))
                index = solve(cmd=arg.cmd,
                              inputs=inputs,
                              arch=arg.arch,
                              type=arg.type,
                              range_start=arg.range_start,
                              range_end=arg.range_end,
                              count_on_branch_taken=arg.count_on_branch_taken,
                              module=arg.module,
                              retry=arg.retry,
                              encoding=arg.encoding)
                if index == -1:
                    exit()
                return m[index]
                # know[m[index]] = right_char
        elif 'normal'.startswith(arg.order):

            def gen_inputs():
                inputs = []
                input_start = ''.join(know.values())
                left_len = length - len(know) - 1
                for char in charset:
                    inputs.append(input_start + char + padding * left_len)
                return inputs

            def get_index():
                return max(know.keys()) + 1 if know else 0
        elif 'reverve'.startswith(arg.order):

            def gen_inputs():
                inputs = []
                input_end = ''.join(know.values())
                left_len = length - len(know) - 1
                for char in charset:
                    inputs.append(padding * left_len + char + input_end)
                return inputs

            def get_index():
                return min(know.keys()) - 1 if know else length - 1

        else:
            exit()

        while len(know) != length:
            # inputs = []

            # input_format = bytearray(length)
            # for key, value in know:
            #     input_format[key] = value
            # input_format = str(input_format, arg.encoding)
            # for char in charset:
            #     inputs.append(input_format.replace('\x00', char))
            inputs = gen_inputs()

            index = solve(cmd=arg.cmd,
                          inputs=inputs,
                          arch=arg.arch,
                          type=arg.type,
                          range_start=arg.range_start,
                          range_end=arg.range_end,
                          count_on_branch_taken=arg.count_on_branch_taken,
                          module=arg.module,
                          retry=arg.retry,
                          encoding=arg.encoding)
            if index == -1:
                exit()

            right_char = charset[index]
            know[get_index()] = right_char