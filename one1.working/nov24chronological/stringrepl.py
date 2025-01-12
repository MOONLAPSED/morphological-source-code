import sys

data = """This is a line.

This is another line.

    This line is indented.
____
<this is junk>
    [[[this is indented junk]]]```python
    def foo():
        pass
    ```
        This is the end of the junk.
- #De-reference
	- & = [[call by reference]] "the address of" (as opposed to "the value of")
	- Before we can #De-reference we have to have a variable and a #pointer with which to [[call by reference]] that variable. For ex (in #C ):
		- 'an integer whose name is 'x' is set to the value 4';
		  int x = 4;
		  'integer pointer named px is set to "the address of" x'
		  int * px = &x;
		- //'an integer whose name is X is set to the value 4'
		  int x = 4;
		  //'integer pointer named pX is set to "the address of" X'
		  int * pX = &X;
		  //an asterisk(*) is placed next to a type, it modifies the type.
		  //ampersand(&) can be verbalized as 'the address of'
		  //--------------------------------------------------------------
		  //we have a pointer the value of x,
		  //but doing anything to/with it is out of scope of any new func.
		  //The solution; an asterisk(*). when used alone it is called a de-reference.
		  //to de-reference is get the value by jumping with the pointer
		  //to go to the address pointed to by the pointer. int y = *pX;
		  //'integer Y is set to the thing pointed to by pX'
		  //this code passed int Y the value of int X by reference.
		  //we copied the value of X to Y which is in-scope and now usable in any func.
            - https://www.youtube.com/watch?v=2ybLD6_2gKM
		-
	-
	-
	-
"""

class DataHomogenizer:
    def __init__(self, data):
        self.data = data
        self.lines = data.splitlines()
        self.line_count = len(self.lines)
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.lines[key]
        else:
            return self.lines[key]
    def __setitem__(self, key, value):
        if isinstance(key, slice):
            self.lines[key] = value
        else:
            self.lines[key] = value
    def __len__(self):
        return self.line_count
    def __str__(self):
        return "\n".join(self.lines)
    def __repr__(self):
        print(f'{self.__class__.__name__}({self.data!r})')
    def __iter__(self):
        return iter(self.lines)
    
def main():
    D = DataHomogenizer(data)
    print(D.data)
    D.__repr__
    pass

if __name__ == "__main__":
    main()