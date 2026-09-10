# Staunt Browser Ultra - Native C++ Launcher

### How to Compile

#### Option 1: Using Microsoft Visual C++ (MSVC cl.exe)
Open Developer Command Prompt for VS and run:
```cmd
cl /O2 /EHsc /DUNICODE /D_UNICODE StauntBrowser.cpp /link /SUBSYSTEM:WINDOWS Shell32.lib Ole32.lib
```

#### Option 2: Using MinGW GCC / Clang
```cmd
g++ -O3 -mwindows -municode StauntBrowser.cpp -o StauntBrowser.exe -lshell32 -lole32
```

This compiles a standalone native 64-bit Windows executable with zero runtime dependencies.
