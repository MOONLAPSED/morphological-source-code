# !cntxt.md - Morphological Source Code (MSC) 

 - There is an assumption inherent in the project that a neural network is a cognitive system. The assumption is that there is something for this cognitive system to do in any given situation, and that it is the cognitive system's job to figure out what that thing is. 
 
 - Upon location of its head/parent, it either orients itself within a cognitive system or creates a new cognitive system.

 - Cognitive systems pass as parameters namespaces, syntaxes, and cognitive systems. Namespaces and syntaxes are in the form of key-value pairs. Cognitive systems are also in the form of key-value pairs, but the values are cognitive systems. **kwargs are used to pass these parameters.

 - "Cognitive systems are defined by actions, orientations within structures, and communicative parameters. 'State' is encoded into these parameters and distributed through the system."

In a nutshell, "Morphological Source Code" is a paradigm in which the source code adapts and morphs in response to real-world interactions, governed by the principles of dynamic runtime configuration and contextual locking mechanisms. The-described is an architecture, only. The kernel agents themselves are sophisticated LLM trained-on ELFs, LLVM compiler code, systemd and unix, python, and C. It will utilize natural language along with the abstraction of time to process cognosis frames and USDs. In our initial experiments "llama" is the presumptive agent, not a specifically trained kernel agent model. The challenge (of this architecture) lies in the 'cognitive lambda calculus' needed to bring these runtimes into existence and evolve them, not the computation itself. Cognosis is designed for consumer hardware and extreme scalability via self-distribution of cognitive systems (amongst constituent [[subscribers|asynchronous stake-holders]]) peer-to-peer, where stake is not-unlike state, but is a function of the cognitive system's ability to contribute to the collective.

### The Free Energy Principle

The Free Energy Principle suggests that biological agents minimize surprise by predicting their sensory inputs. This principle can be applied to data processing, transforming high-dimensional data into lower-dimensional representations that are easier to model and predict.

## Epigentics and Quine-like behavior

```python
import inspect

class Bootstrapper:
    def __init__(self):
        # Load its own source code
        self.source_code = inspect.getsource(self.__class__)

    def display_source(self):
        print("---- Self Source Code ----")
        print(self.source_code)

    def save_self(self, new_code, filename="bootstrapper_next.py"):
        with open(filename, "w") as f:
            f.write(new_code)
        print(f"Saved evolved version to {filename}")

# Start the bootstrapper
if __name__ == "__main__":
    b = Bootstrapper()
    b.display_source()
```

Python, the interpreted language ascendent in ML, science, and beyond, is used here to demonstrate the bootstrapping of a self-modifying code. The Bootstrapper is not a kernel agent, but a simple example of how a program can modify its own source code; "'Quine-like' behavior". To 'Quine' is to simply replicate the source code of the runtime interpreted by the runtime itself. This is critical to understand, so go-ahead and run the code in a '.py' file to see it do its 'SmallTalk' (coloquially, what we call the first class function first class image true-OOP of the Cognosis architecture).