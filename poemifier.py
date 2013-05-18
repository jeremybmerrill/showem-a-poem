#!/usr/bin/python
# -*- coding: utf-8 -*-

from rhymechecker import RhymeChecker
from random import randint
import sys
"""
Architecture:
  1. For each validation type (e.g. syllable count, rhyming, eventually stress), create a "hash" dicts.
    a. Each dict is of the form: hash_value -> [line1, line2, line3]
    b. each hash_value is computed by hash(line) where the syllable_hash function returns syllable length of the line and rhyme_hash returns the rime (i.e. nucleus + coda) of the final syllable of the line.
  2. Discard or ignore all syllable_hash_dict entries whose syllable counts are not in the format.
  3: Optionally, pair stuff, e.g. rhyming pairs or triplets (or n-lets where n is the greatest amount of rhyming lines needed in the format, e.g. 3 for a limerick, , but only 2 for a sonnet.) and, if necessary, of the right syllable length.
  4. From these pairs, assemble a poem.

  e.g. python poemifier.py sonnet ./SCALIA.txt 
"""

#TODO: use espeak, add pitch to "sing" the poems

class Poemifier:
  def __init__(self, format_name, format=None):
    """Specify the name of a known format or specify a fully-defined format."""
    #TODO specify a name (req) and optionally the format specification
    self.formats = {
        "haiku" : {"syllable_structure" : [5,7,5],
                   "rhyme_scheme" : "abc"},
        "limerick" : {"syllable_structure" : [(9,11),(9, 11),6,6,(9, 11)], 
                       "rhyme_scheme" : "aabba"},
        "sonnet" : {"syllable_structure" : [10],
                      "rhyme_scheme" :  "ababcdcdefefgg"}
      }
    self.debug = False
    #self.poem_complete = False #dunno what this is.
    #self.poem_validator = PoemValidator()
    if not format:
      self.format_name = format_name
    else:
      self.format_name = format_name
      self.formats[format_name] = format #potentially temporarily overwriting a predefined format. That's okay.
    self.format = self._fill_out_format(self.formats[format_name])
    self.lines_needed = self.format["lines_needed"]

    #self.poems = [ [None] * self.lines_needed ] 

    self.rhyme_checker = RhymeChecker()
    self.rhyme_checker.debug = False

    #TODO abstract away hash types by format.
    self.rhyme_dict = {}
    self.syllable_count_dict = {}

  def _fill_out_format(self, format):
    if "lines_needed" not in format:
      format["lines_needed"] = max(len(format["syllable_structure"]), len(format["rhyme_scheme"]))
      lines_needed = format["lines_needed"]
    rhyme_scheme = format["rhyme_scheme"] * (lines_needed / len(format["rhyme_scheme"]))
    if len(format["syllable_structure"]) < lines_needed:
      multiple = float(lines_needed) / len(format["syllable_structure"])
      if multiple % 1.0 != 0.0:
        raise TypeError, "Invalid poem format :("
      format["syllable_structure"] = int(multiple) * format["syllable_structure"]
    if len(format["rhyme_scheme"]) < lines_needed:
      multiple = float(lines_needed) / len(format["rhyme_scheme"])
      if multiple % 1.0 != 0.0:
        raise TypeError, "Invalid poem format :("
      format["rhyme_scheme"] = int(multiple) * format["rhyme_scheme"]
    format["unique_syllable_structure"] = set()
    for syllable_count_item in format["syllable_structure"]:
      format["unique_syllable_structure"].add(syllable_count_item)
    format["syllable_count_to_syllable_count_token"] = {}

    for syllable_count_item in format["syllable_structure"]:
      if isinstance(syllable_count_item, int):
        if syllable_count_item not in format["syllable_count_to_syllable_count_token"].keys():
          format["syllable_count_to_syllable_count_token"][syllable_count_item] = set()
        format["syllable_count_to_syllable_count_token"][syllable_count_item].add(syllable_count_item)
      elif isinstance(syllable_count_item, tuple):
        for num in range(syllable_count_item[0],syllable_count_item[1]+1):
          if num not in format["syllable_count_to_syllable_count_token"].keys():
            format["syllable_count_to_syllable_count_token"][num] = set()
          format["syllable_count_to_syllable_count_token"][num].add(syllable_count_item)
    return format

  def _rime(self, line):
    """Return this line's last word's rime to use as key to this value in the rhyme hash."""
    rime = self.rhyme_checker.get_rime(line.split(" ")[-1])
    if rime:
      return tuple(rime)
    else:
      return False

  def _syllable_count(self, line):
    """return this line's syllable count to use as key to this value in the syllable_count hash."""
    return sum(map(self.rhyme_checker.count_syllables, line.split(" ")))

  def try_line(self, line):
    """ Add a line, then return True if, given that line, a poem can be created."""
    self.add_line(line)
    #TODO: split line here.
    return self.get_poem() #False or a poem.

  def add_line(self, line):
    """
    Adds a line to the format hash dicts. Return False if the line cannot be used.
    """
    #TODO: abstract away format stuff
    # format_items = [[self._rime, self.rhyme_dict], [self._syllable_count, self.syllable_count_dict]]
    # for hashFunc, format_hash_dict in format_items:

    #try splitting line and call _add_line_helper on that.

    splits = []
    for syllable_count_token in self.format["unique_syllable_structure"]:
      splits += self.split_line_at_syllable_count(line, syllable_count_token)
    for split in splits:
      #TODO: figure out a way to put these together.
      for inner_split in split:
        self._add_line_helper(inner_split)
    return self._add_line_helper(line)

  def _add_line_helper(self, line):
    syll_count = self._syllable_count(line)
    if syll_count in self.format["syllable_count_to_syllable_count_token"].keys(): #TODO: obviously, abstract this.
      rime = self._rime(line)
      if not rime:
        return False
      rime = tuple(rime)
      for syll_count_token in self.format["syllable_count_to_syllable_count_token"][syll_count]:
        if syll_count_token not in self.syllable_count_dict:
          self.syllable_count_dict[syll_count_token] = []
        self.syllable_count_dict[syll_count_token].append(line)

        if rime not in self.rhyme_dict:
          self.rhyme_dict[rime] = {}
        if syll_count_token not in self.rhyme_dict[rime]:
          self.rhyme_dict[rime][syll_count_token] = []
        self.rhyme_dict[rime][syll_count_token].append(line)
      return True
    else:
      return False

  def split_line_at_syllable_count(self, line, syllable_count):
    """Returns a line split at the given number(s) of syllables. 

    If a range, return a list of possibilities.
    E.g. for sentence "a man a plan" and range 1,3, 
    Should this return [["a", "man a plan"], ["a man", "a plan"], ["a man a", "plan"]]?

    >>> p = Poemifier("haiku")
    >>> p.split_line_at_syllable_count("There once was banana man from the beach", 4)
    []
    >>> p.split_line_at_syllable_count("There once was a man from the beach", 4)
    [['There once was a', 'man from the beach']]
    >>> p.split_line_at_syllable_count("There once was a man from the beach banana", 4)
    [['There once was a', 'man from the beach banana']]
    >>> p.split_line_at_syllable_count("There once was banana people from the beach", (5,7))
    [['There once was banana', 'people from the beach']]
    >>> p.split_line_at_syllable_count("There once was banana man from the beach Anna", (5,7))
    [['There once was banana', 'man from the beach Anna'], ['There once was banana man', 'from the beach Anna']]
    """

    if isinstance(syllable_count, int):
      splits = [self._split_line_at_syllable_count_helper(line, syllable_count)]
    elif isinstance(syllable_count, tuple):
      splits = map(lambda s: self._split_line_at_syllable_count_helper(line, s), range(syllable_count[0], syllable_count[1]+1))
    return filter(lambda x: x is not False, splits) or []

  def _split_line_at_syllable_count_helper(self, line, syllable_count):
    split_line = line.strip().split(" ")
    if "" in split_line:
      return False
    if syllable_count == 0:
      return ["", line]
    elif syllable_count > 0:
      word = split_line[0]
      this_word_syllables = self.rhyme_checker.count_syllables(word)
      next_return =  self._split_line_at_syllable_count_helper(" ".join(split_line[1:]), syllable_count - this_word_syllables)
      if next_return:
        next_return[0] = " ".join([word] + filter(lambda x: x != "", next_return[0].split(" ")))
        return next_return
      else:
        return False
    else:
      return False


  def validate_rhyme(self, poem, line, index):
    """True if this line fits in the rhyme scheme where it is."""
    temp_poem = list(poem) #"copy" the list
    temp_poem[index] = line

    last_word = line.split(" ")[-1]
    last_word.strip(".,?!:;\" ")
    #does it fit where it is.
    rhyme_symbol = self.format["rhyme_scheme"][index]
    lines_to_compare_to = [temp_poem[i] for i, symbol in enumerate(self.format["rhyme_scheme"]) if symbol == rhyme_symbol and temp_poem[i] and i != index]
    if not lines_to_compare_to:
      if self.debug:
        print "nothing to compare " + last_word + " to. " 
      return True
    words_to_compare_to = map(lambda x: x.split(" ")[-1], lines_to_compare_to )
    return True in map(lambda x: self.rhyme_checker.rhymes_with(last_word, x), words_to_compare_to)

  def _pair_rhyme_lines(self):
    """Pair lines that rhyme."""
    #all the lines in any of the dicts are guaranteed to be of acceptable length.
    #pairs = {"EH" => {6 => ["a", "b", "c"], (9,11) => ["a", "b", "c"]}, "OI" => ...}
    pairs_by_rhyme = {}
    pairs_by_syll_count = {}
    for rime, rhyme_groups in self.rhyme_dict.items():
      if len(rhyme_groups) == 1 and len(rhyme_groups.values()[0]) == 1:
        #print("skipping something while pairing")
        continue
      inner_pairs_by_syll_count = {}
      for syllable_count_token, rhyme_group in rhyme_groups.items():

        #exclude words from the rhyme group whose last word is the last word of another line in this rhyme group
        already_used_last_words = set()
        new_rhyme_group = []
        for rhyme_line in rhyme_group:
          if rhyme_line.split(" ")[-1] not in already_used_last_words:
            already_used_last_words.add(rhyme_line.split(" ")[-1])
            new_rhyme_group.append(rhyme_line)

        inner_pairs_by_syll_count[syllable_count_token] = new_rhyme_group
        if syllable_count_token not in pairs_by_syll_count.keys():
          pairs_by_syll_count[syllable_count_token] = {}
        pairs_by_syll_count[syllable_count_token][rime] = new_rhyme_group
      pairs_by_rhyme[rime] = inner_pairs_by_syll_count
    return pairs_by_syll_count

  def get_poem(self, random=False):
    """ Return False or a poem. """
    #TODO: again, abstraction!
    poem = [None] * self.format["lines_needed"]
    if self.format["rhyme_scheme"]:
      #print "pairs: " +  str(self._pair_rhyme_lines())
      pairs = self._pair_rhyme_lines()
      for syllable_count_token in self.format["unique_syllable_structure"]:
        if syllable_count_token not in pairs:
          return None
        candidate_lines = filter(lambda rhymes: len(rhymes) >= self.format["syllable_structure"].count(syllable_count_token), pairs[syllable_count_token].values())
        if not candidate_lines:
          return None
        this_sylls_lines = list(candidate_lines[randint(0,len(candidate_lines) - 1) if random else 0 ])
        for index, syllable_count in enumerate(self.format["syllable_structure"]):
          if syllable_count == syllable_count_token:
            poem[index] = this_sylls_lines.pop()
      return poem
    elif self.format["syllable_structure"]:
      #TODO: delete all the hash entries that don't fit anything in the syllable structure
      raise ShitsFuckedException # I think this is dead code.
      for index, syllable_count in enumerate(self.format["syllable_structure"]):
        if syllable_count not in self.syllable_count_dict:
          return None 
        candidate_lines = filter(lambda l: l not in poem, self.syllable_count_dict[syllable_count])
        if not candidate_lines:
          return None
        if random:
          next_line_index = randint(0,len(candidate_lines) - 1)
        else:
          next_line_index = 0
        next_line = candidate_lines[next_line_index]
        poem[index] = next_line
      return poem

def _test():
  import doctest
  doctest.testmod()

class ShitsFuckedException(Exception):
  pass


if __name__ == "__main__":
  import re
  poem_format = sys.argv[1]
  input_text = sys.argv[2] or "./SCALIA.txt"

  lists_of_lines = map(lambda x: x.split(","), open(sys.argv[2]).read().split("\n"))

  lines = [line for line_list in lists_of_lines for line in line_list]

  #lines = ["camping is in tents", "my tree table tries", "between those times I slept none"]
  # lines = ["many words in english rhyme with song", "one two three four five six", "a bee see dee word kicks",
  #  "This is a line that is twenty long", "here are ten more ending in wrong", "Jeremy Bee Merrill plays ping pong",
  #  ]

  p = Poemifier(poem_format)
  p.debug = True
  #this can't be a do... while, because we have to add all the lines, then do various processing steps.
  for line in lines:
    if "No. " in line:
      continue
    line = re.sub("[^A-Za-z ']", "", line)
    line = line.strip()
    if re.search("\s[BCDEFGHJKLMNOPQRSTUVWXYZ]\s", line): #if it contains any abbreviations
      continue
    p.try_line(line)
    # if p.try_line(line):
    #   if p.debug: 
    #     print "Done!"
    #   break
    # print p.syllable_count_dict
    # print p.rhyme_dict
    # print ""
  print ""
  print p.get_poem(True)


#TODO: make split lines work.

#TODO: (eventually)
# Allow multiple poems to be requested (only break when the number of complete poems in self.poems = the number requested)