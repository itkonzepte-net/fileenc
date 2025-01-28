# fileenc
A small cli tool for aes encryption of files.

By using fileenc you acknowledge the security weakness mentioned in the security section as well as its caveats.

## Install (from source)
Build fileenc binary using the go toolchain and copy it to one of your directories in the PATH environment. You can also run 
fileenc from a local directory which may require you to qualify the location of fileenc according to your OS and shell.

## Install (from binary)
Download the according binary and put it into a directory of a PATH environment. You can also run 
fileenc from a local directory which may require you to qualify the location of fileenc according to your OS and shell.

## Usage

### General

`fileenc -source <file> -key <key> [-decrypt]` 

fileenc will read the provided file and create a file <file>.enc that contains the encrypted contents using the provided <key>. 
If -decrypt is provided reads the file <file>.enc and writes it into <file>

<key> must be 16, 24 or 32 characters long!

### Example

Encrypt text.txt to text.txt.enc (creates or overwrites file text.txt.enc)

```sh
fileenc -source text.txt -key ThisPassIsNtSafe
```

Decrypt (creates or overwrites text.txt)

```sh
fileenc -source text.txt -key ThisPassIsNtSafe -decrypt
```

## Security

fileenc does not take special precautions against attacks of any kind including side-channel attacks or leftover remainders in memory. fileenc's output
can be transmitted over an insecure channel but fileenc does not ensure integrity at any level. It does not protect you against data corruption. 

## Caveats

Does not check for passwords correctness. Uses password to generate encryption/decryption key and hence in case of a wrong
password you'll get data garbage. 

Will overwrite existing files if `-override` flag is present. Make sure to keep important data out of reach!

## Contribute

Contribution is welcome.
