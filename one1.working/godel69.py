import itertools
import logging
import random
from typing import List, Tuple, Dict
from decimal import Decimal, getcontext

# Use Decimal with a higher precision for large numbers if needed
getcontext().prec = 100

# Set up logging with UTF-8 encoding for broader character support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('turing_machine.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger('TuringMachine')

class TuringMachine:
    def __init__(self, 
                 states: List[str], 
                 tape_alphabet: List[str], 
                 tape: List[str],
                 blank: str, 
                 transitions: Dict[Tuple[str, str], Tuple[str, str, str]],
                 start_state: str, 
                 accept_state: str,
                 reject_state: str,
                 initial_godel: int = None):
        logger.info("Initializing Turing Machine")
        
        self.states = states
        self.tape_alphabet = tape_alphabet
        self.blank = blank
        self.transitions = transitions
        self.accept_state = accept_state
        self.reject_state = reject_state
        
        if initial_godel is not None:
            logger.info(f"Initializing from Gödel number: {initial_godel}")
            self.state, self.tape, self.head_position = self.decode_state_godel(initial_godel, len(tape))
        else:
            logger.info("Initializing from direct values")
            self.state = start_state
            self.tape = tape.copy()
            self.head_position = 0
        
        logger.info(f"Initial configuration: {self}")

    def decode_state_godel(self, godel_number: int, tape_length: int):
        logger.info(f"Decoding Gödel number: {godel_number}")
        number = Decimal(godel_number)
        primes = list(itertools.islice(self.prime_generator(), tape_length + 2))
        
        # Decode head position
        head_position = self._decode_factor(number, primes[-1]) - 1
        if head_position < 0 or head_position >= tape_length:
            raise ValueError("Invalid head position decoded")
        
        # Decode state
        state_index = self._decode_factor(number, primes[0]) - 1
        if state_index < 0 or state_index >= len(self.states):
            raise ValueError("Invalid state index decoded")
        state = self.states[state_index]
        
        # Decode tape
        tape = []
        for i in range(tape_length):
            prime = primes[i + 1]
            symbol_index = self._decode_factor(number, prime) - 1
            if symbol_index < 0 or symbol_index >= len(self.tape_alphabet):
                raise ValueError(f"Invalid symbol index at position {i} decoded")
            tape.append(self.tape_alphabet[symbol_index - 1] if symbol_index > 0 else self.blank)
        
        logger.info(f"Decoded configuration: State: {state}, Tape: '{''.join(tape)}', Head: {head_position}")
        return state, tape, head_position

    def step(self):
        if self.state in [self.accept_state, self.reject_state]:
            logger.debug(f"Machine in halting state: {self.state}")
            return
        
        current_symbol = self.tape[self.head_position]
        logger.debug(f"State: {self.state}, Symbol: {current_symbol}, Position: {self.head_position}")
        
        transition_key = (self.state, current_symbol)
        if transition_key in self.transitions:
            new_state, new_symbol, direction = self.transitions[transition_key]
            logger.debug(f"Transition: {transition_key} -> ({new_state}, {new_symbol}, {direction})")
            
            self.tape[self.head_position] = new_symbol
            self.state = new_state
            self.move_head(direction)
        else:
            logger.warning(f"No transition for {transition_key}")
            self.state = self.reject_state
        
        logger.debug(f"New configuration: {self}")

    def move_head(self, direction: str):
        if direction == 'R':
            self.head_position += 1
            if self.head_position >= len(self.tape):
                logger.debug("Extending tape right")
                self.tape.append(self.blank)
        elif direction == 'L':
            self.head_position -= 1
            if self.head_position < 0:
                logger.debug("Extending tape left")
                self.tape.insert(0, self.blank)
                self.head_position = 0

    def encode_state_godel(self) -> Decimal:
        logger.info("Encoding machine state to Gödel number")
        state_index = self.states.index(self.state) + 1
        tape_indices = [self.tape_alphabet.index(symbol) + 1 for symbol in self.tape]
        head_adjusted = self.head_position + 1 
        primes = list(itertools.islice(self.prime_generator(), len(tape_indices) + 2))
        godel_number = Decimal(primes[0] ** state_index) * Decimal(primes[-1] ** head_adjusted)
        for i, symbol_index in enumerate(tape_indices):
            godel_number *= Decimal(primes[i + 1] ** symbol_index)
        
        logger.debug(f"Encoded Gödel number: {godel_number}")
        return godel_number

    def prime_generator(self):
        D = {}
        q = 2
        while True:
            if q not in D:
                yield q
                D[q * q] = [q]
            else:
                for p in D[q]:
                    D.setdefault(p + q, []).append(p)
                del D[q]
            q += 1

    def run(self):
        logger.info("Running Turing Machine")
        steps = 0
        while self.state not in [self.accept_state, self.reject_state]:
            self.step()
            steps += 1
        logger.info(f"Machine halted after {steps} steps in state {self.state}")
        return steps

    def _decode_factor(self, number: Decimal, prime: int) -> int:
        factor = 0
        while number % prime == 0:
            number /= prime
            factor += 1
            logger.debug(f"Decoded factor: {factor}, Remaining number: {number}")
        return factor

    def perturb_tape(self, new_tape: List[str]):
        """Change the tape content."""
        logger.info(f"Perturbing tape to: {new_tape}")
        self.tape = new_tape.copy()

    def perturb_initial_state(self, new_start_state: str):
        """Change the initial state."""
        if new_start_state in self.states:
            logger.info(f"Perturbing initial state to: {new_start_state}")
            self.state = new_start_state
        else:
            raise ValueError(f"Invalid state: {new_start_state}")

    def perturb_transitions(self, perturbation_rate: float = 0.1):
        """Perturb the transitions randomly."""
        perturbed_transitions = self.transitions.copy()
        for key in list(perturbed_transitions.keys()):
            if random.random() < perturbation_rate:
                new_state = random.choice(self.states)
                new_symbol = random.choice(self.tape_alphabet)
                new_direction = random.choice(['L', 'R'])
                perturbed_transitions[key] = (new_state, new_symbol, new_direction)
                logger.info(f"Perturbed transition {key} -> {perturbed_transitions[key]}")
        self.transitions = perturbed_transitions

    def generate_random_godel_number(self, tape_length: int, head_position: int):
        """Generate a random Gödel number for initialization."""
        state_index = self.states.index(random.choice(self.states)) + 1
        tape_indices = [self.tape_alphabet.index(random.choice(self.tape_alphabet)) + 1 for _ in range(tape_length)]
        head_adjusted = head_position + 1 
        primes = list(itertools.islice(self.prime_generator(), tape_length + 2))
        godel_number = Decimal(primes[0] ** state_index) * Decimal(primes[-1] ** head_adjusted)
        for i, symbol_index in enumerate(tape_indices):
            godel_number *= Decimal(primes[i + 1] ** symbol_index)
        return godel_number

    def __str__(self):
        tape_str = ''.join(self.tape).replace(' ', '_')
        return f'State: {self.state}, Tape: {tape_str}, Head: {self.head_position}'

if __name__ == "__main__":
    logger.info("Starting Turing Machine program")

    states = ['q0', 'q1', 'qAccept', 'qReject']
    tape_alphabet = ['0', '1', '_']
    tape = ['1', '0', '1', '_']
    blank = '_'
    transitions = {
        ('q0', '1'): ('q1', '0', 'R'),
        ('q0', '0'): ('q0', '1', 'R'),
        ('q1', '1'): ('q0', '0', 'L'),
        ('q1', '0'): ('q1', '1', 'R'),
        ('q0', '_'): ('qAccept', '_', 'R'),
        ('q1', '_'): ('qReject', '_', 'R'),  # Changed to allow exiting loop
    }
    start_state = 'q0'
    accept_state = 'qAccept'
    reject_state = 'qReject'

    tm = TuringMachine(states, tape_alphabet, tape, blank, transitions, 
                       start_state, accept_state, reject_state)

    # Perturb the tape content
    tm.perturb_tape(['0', '1', '1', '_'])

    # Perturb the initial state
    tm.perturb_initial_state('q1')

    # Perturb the transitions
    tm.perturb_transitions(perturbation_rate=0.1)

    # Generate a random Gödel number for initialization
    random_godel_number = tm.generate_random_godel_number(len(tape), 2)
    tm = TuringMachine(states, tape_alphabet, tape, blank, transitions, 
                       start_state, accept_state, reject_state, initial_godel=random_godel_number)

    steps = tm.run()
    logger.info(f"Machine completed in {steps} steps")
    final_godel = tm.encode_state_godel()
    logger.info(f"Final state Gödel number: {final_godel}")