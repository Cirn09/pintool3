# Pintool3

Inspired by [pintool](https://github.com/wagiro/pintool) and [pintool_ctf](https://github.com/NoOne-hub/pintools_ctf).


This tool can be useful for solving some reversing challenges in CTFs events. Implements the technique described here:

- http://shell-storm.org/blog/A-binary-analysis-count-me-if-you-can/

### Feature

- Fast: only count branch Instructions in main executable and multi-process support

- Python 3
- Easy to reprogramming (maybe)
- Windows, Linux and MacOS support (maybe, I don't have a Mac to test)


### Configuration
You must write config file in `` ~/.config/pintool3.conf`` (Linux) or `%USERPROFILE%\\.config\\pintool3.conf` (Windows) or `/i/do/not/know/.config/pintool3.conf` (MacOS).

```ini
[path]
pin = PATH_TO_PIN
bcount32 = PATH_TO_BCOUNT32
bcount64 = PATH_TO_BCOUNT64
```

### Help



```sh
$python pintool3.py 
usage: pintool3 [options] -- cmd
example: pintool3 -a 64 -- ls -l

positional arguments:
  cmd                   Command line for playing with Pin Tool

optional arguments:
  -h, --help            show this help message and exit
  -a ARCH, --arch ARCH  Program architecture 32 or 64 bits, -a 32 or -a 64
  -m MODULE, --module MODULE
                        Module name to count, -u exam.dll (default *.exe)
  -s RANGE_START, --range-start RANGE_START
                        Start *offset* of the record range.
  -e RANGE_END, --range-end RANGE_END
                        End *offset* of the record range. 0 mean module end.
  -b, --count-on-branch-taken
                        Count all branch or just taken branch. (default: false)
  --disable-multiprocess
                        Disable multiprocess
  -r RETRY, --retry RETRY
                        Retry times.
  --encoding ENCODING   Input encoding.
  -d, --detect          Try detech expected input length.
  -c CHARSET, --charset CHARSET
                        Charset definition for brute force. -c "abc..." (default: string.printable-string.whitespace)
  -p PADDING, --padding PADDING
                        padding (default: '\').
  -l LENGTH, --length LENGTH
                        Input length or max input length (when detect on).
  -t TYPE, --type TYPE  max or min
  -o ORDER, --order ORDER
                        Bruteforce order, "normal", "reverse" or "detect"
```


### Examples
**languages binding - Byte2021**

```
❯ py -3 .\pintool3.py -a64 -s 0xcc240 -e 0x103dab -d .\byte2021q_languages_binding\new_lang.exe .\byte2021q_languages_binding\new_lang_script.out
  \\\\                                    | 19148
  \\\\\                                   | 19152
  \\\\\\                                  | 19146
  \\\\\\\                                 | 19150
  \\\\\\\\                                | 19148
  \\\\\\\\\                               | 19154
  \\\\\\\\\\                              | 19152
  \\\\\\\\\\\                             | 19148
  \\\\\\\\\\\\                            | 19148
  \\\\\\\\\\\\\                           | 19146
  \\\\\\\\\\\\\\                          | 19148
  \\\\\\\\\\\\\\\                         | 19150
  \\\\\\\\\\\\\\\\                        | 19146
  \\\\\\\\\\\\\\\\\                       | 19150
  \\\\\\\\\\\\\\\\\\                      | 19148
  \\\\\\\\\\\\\\\\\\\                     | 19148
  \\\\\\\\\\\\\\\\\\\\                    | 19148
  \\\\\\\\\\\\\\\\\\\\\                   | 19148
  \\\\\\\\\\\\\\\\\\\\\\                  | 19148
  \\\\\\\\\\\\\\\\\\\\\\\                 | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\                | 19148
  \\\\\\\\\\\\\\\\\\\\\\\\\               | 19148
  \\\\\\\\\\\\\\\\\\\\\\\\\\              | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\\\\             | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\            | 19146
* \\\\\\\\\\\\\\\\\\\\\\\\\\\\\           | 21263
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\          | 19148
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\         | 19148
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\        | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\       | 19152
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\      | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\     | 19154
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\    | 19156
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\   | 19152
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  | 19150
  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ | 19152
> \\\\\\\\\\\\\\\\\\\\\\\\\\\\\           | 21263
The expected input length may be 29
```

```
❯ py -3 .\pintool3.py -a64 -s 0xcc240 -e 0x103dab -l29 -b .\byte2021q_languages_binding\new_lang.exe .\byte2021q_languages_binding\new_lang_script.out
  0\\\\\\\\\\\\\\\\\\\\\\\\\\\\ | 10480
  1\\\\\\\\\\\\\\\\\\\\\\\\\\\\ | 10480
...
> B\\\\\\\\\\\\\\\\\\\\\\\\\\\\ | 10598
...
> By\\\\\\\\\\\\\\\\\\\\\\\\\\\ | 10718
...
> Byt\\\\\\\\\\\\\\\\\\\\\\\\\\ | 10848
...
> Byte\\\\\\\\\\\\\\\\\\\\\\\\\ | 10958
...
> ByteC\\\\\\\\\\\\\\\\\\\\\\\\ | 11080
```

note: Because GoLang's influence on the signal and thread management code is enough to cover the count of the check function, this problem requires careful selection of the range before you can use pintool3 to solve the part of the flag checked by GoLang (obviously, the range I selected is not fine enough).

### TODO

todo
