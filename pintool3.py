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

class Pinfo(object):
    def __init__(self, out, err, count) -> None:
        self.out = out
        self.err = err
        self.count = count

def pin(cmd: list,
        input: str,
        arch: int,
        range_start: int = 0,
        range_end: int = 0,
        count_on: int = 0,
        module: str = '',
        retry: int = 0,
        encoding: str = 'utf8') -> Pinfo:
    '''`cmd < input` -> Pinfo'''
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
        _cmd += f' -b {count_on}'
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
        _cmd += ['-b', str(count_on)]
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
                env=os.environ,
                input=input_encode,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            info = str(p.stderr, encoding)
            if t := re.search(r, info):
                count = t.groups()[0]
                count = int(count)
                return Pinfo(p.stdout, p.stderr, count)
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
             count_on: int = 0,
             module: str = '',
             retry: int = 0,
             encoding: str = 'utf8') -> list:
    '`cmd < [input0, input1 ...]` -> [Pinfo0, Pinfo1 ...]'
    pool = Pool(initializer=init_worker)
    try:
        r = []
        for input in inputs:
            m = pool.apply_async(pin,
                                 (cmd, input, arch, range_start, range_end,
                                  count_on, module, retry, encoding))
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


def select(array: list, type: str) -> int:
    if type == 'max':
        max_index = max(range(len(array)), key=lambda x: array[x])
        max_value = array[max_index]
        if array.count(max_value) != 1:
            return -1
        else:
            return max_index
    elif type == 'min':
        min_index = min(range(len(array)), key=lambda x: array[x])
        min_value = array[min_index]
        if array.count(min_value) != 1:
            return -1
        else:
            return min_index
    elif type == 'unique':
        if len(array) <= 2:
            return -1
        s = set(array)
        if len(s) != 2:
            return -1
        t = sorted(array)
        start = t[0]
        mid = t[len(array) // 2]
        end = t[-1]
        if start != mid:
            return array.index(start)
        elif end != mid:
            return array.index(end)
        else:
            # never
            return -1
    else:
        return -1


def solve_single(cmd: list,
                 inputs: list,
                 arch: int,
                 type: str = 'max',
                 range_start: int = 0,
                 range_end: int = 0,
                 count_on: int = 0,
                 module: str = '',
                 retry: int = 0,
                 encoding: str = 'utf8') -> int:
    '`cmd < [input0, input1 ...]` -> right index'
    max_input_len = max(map(len, inputs))
    counts = []

    print('=' * 42)
    for input in inputs:
        pinfo = pin(cmd, input, arch, range_start, range_end, count_on, module,
                    retry, encoding)
        count = pinfo.count
        counts.append(count)
        s = '  '
        s += input.ljust(max_input_len, ' ')
        s += ' | ' + str(count)
        print(s)

    target_index = select(counts, type)
    if target_index == -1:
        print('pin failed')
        exit()
    target_count = counts[target_index]
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
                count_on: int = 0,
                module: str = '',
                retry: int = 0,
                encoding: str = 'utf8') -> int:
    '`cmd < [input0, input1 ...]` -> right index'
    pinfos = multipin(cmd, inputs, arch, range_start, range_end, count_on,
                      module, retry, encoding)
    counts = [x.count for x in pinfos]

    target_index = select(counts, type)

    max_input_len = max(map(len, inputs))
    max_count_len = max(
        map(lambda x: math.ceil(math.log10(x)) if x else 1, counts))

    print('=' * 42)
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

    if target_index == -1:
        print('pin failed')
        exit()
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
               count_on: int = 0,
               module: str = '',
               retry: int = 0,
               encoding: str = 'utf8') -> int:
    if multiprocess:
        solve = solve_multi
    else:
        solve = solve_single
    inputs = [char * len for len in range(min_length, max_length + 1)]
    target = solve(cmd, inputs, arch, type, range_start, range_end, count_on,
                   module, retry, encoding)
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
        '--count-type',
        dest='count_on',
        type=int,
        default=0,
        help=
        'Count on (default: 0): \n\t0. all branch \n\t1. taken branch \n\t2. not taken branch.'
    )
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
                        help='Try detech expected input length, then exit.')
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
                        default='_',
                        help="padding (default: '_').")
    parser.add_argument(
        '-k',
        '--known',
        dest='known',
        type=str,
        default='',
        help=
        'input format of flag. Example: "flag{__025______}"\npadding "_" refers to unknown, you can use -p to specify padding.\nAfter setting this option, Length (-l) will be ignored.'
    )
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
                        help='max, min or unique')
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
    length = arg.length

    if arg.detect:
        length = len_detect(cmd=arg.cmd,
                            arch=arg.arch,
                            multiprocess=not arg.disable_multiprocess,
                            max_length=arg.length,
                            char=arg.padding,
                            type=arg.type,
                            range_start=arg.range_start,
                            range_end=arg.range_end,
                            count_on=arg.count_on,
                            module=arg.module,
                            retry=arg.retry,
                            encoding=arg.encoding)
        exit()

    known = {}
    charset = arg.charset
    padding = arg.padding
    right_char = ''

    if arg.known:
        length = len(arg.known)
        for i, c in enumerate(arg.known):
            if c != padding:
                known[i] = c
    if arg.disable_multiprocess:
        solve = solve_single
    else:
        solve = solve_multi

    if 'detect'.startswith(arg.order):

        def gen_inputs():
            inputs = []

            input_format = ['\x00'] * length
            for key, value in known.items():
                input_format[key] = value
            input_format = ''.join(input_format)
            for char in charset:
                inputs.append(input_format.replace('\x00', char))
            return inputs

        def get_index():

            inputs = []
            m = {}
            input_format = ['\x00'] * length
            for key, value in known.items():
                input_format[key] = value
            input_format = ''.join(input_format)
            for i in range(length):
                if i not in known:
                    m[len(inputs)] = i
                    input = input_format[0:i] + right_char + input_format[i+1:]
                    inputs.append(input.replace('\x00', padding))
            index = solve(cmd=arg.cmd,
                          inputs=inputs,
                          arch=arg.arch,
                          type=arg.type,
                          range_start=arg.range_start,
                          range_end=arg.range_end,
                          count_on=arg.count_on,
                          module=arg.module,
                          retry=arg.retry,
                          encoding=arg.encoding)
            if index == -1:
                exit()
            return m[index]

    elif 'normal'.startswith(arg.order):

        def gen_inputs():
            inputs = []
            current = 0
            for i in range(length):
                if i not in known:
                    current = i
                    break
            input = [padding] * length
            for i, v in known.items():
                input[i] = v
            for char in charset:
                input[current] = char
                inputs.append(''.join(input))
            return inputs

        def get_index():
            for i in range(length):
                if i not in known:
                    return i
    elif 'reverve'.startswith(arg.order):

        def gen_inputs():
            inputs = []
            current = 0
            for i in range(length - 1, -1, -1):
                if i not in known:
                    current = i
                    break
            input = [padding] * length
            for i, v in known.items():
                input[i] = v
            for char in charset:
                input[current] = char
                inputs.append(''.join(input))
            return inputs

        def get_index():
            for i in range(length - 1, -1, -1):
                if i not in known:
                    return i

    else:
        exit()

    while len(known) != length:
        inputs = gen_inputs()

        index = solve(cmd=arg.cmd,
                      inputs=inputs,
                      arch=arg.arch,
                      type=arg.type,
                      range_start=arg.range_start,
                      range_end=arg.range_end,
                      count_on=arg.count_on,
                      module=arg.module,
                      retry=arg.retry,
                      encoding=arg.encoding)
        if index == -1:
            exit()

        right_char = charset[index]
        known[get_index()] = right_char