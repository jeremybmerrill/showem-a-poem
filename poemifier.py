#!/usr/bin/python
# -*- coding: utf-8 -*-

from rhymetime import RhymeChecker, Pronunciation, Syllabification, Syllable
from random import randint, shuffle, choice
import re
import sys
import poemformat
from line import Line
import nltk.tokenize.punkt
import nltk.data

import cPickle as pickle

debug_lines = ["camping is in tents", "my tree table tries", "between those times I slept none"]

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

#TODO: make a Heroku/Flask-based app for people to make their own poems.

class Poemifier:
  def __init__(self, poem, **kwargs):
    """Specify the name of a known format or specify a fully-defined format."""
    self.debug = False
    #self.poem_complete = False #dunno what this is.
    #self.poem_validator = PoemValidator()

    self.format = poem.get_format()
    self.lines_needed = self.format["lines_needed"]

    if 'rhyme_checker' in kwargs:
      self.rhyme_checker = kwargs['rhyme_checker']
    else:
      self.rhyme_checker = RhymeChecker()
    self.rhyme_checker.debug = False

    self.allow_partial_lines = False
    self.verbose = False
    self.where_to_put_partial_lines = {}

    #TODO abstract away hash types by format.
    self.rhyme_dict = {}
    self.syllable_count_dict = {}
    # self.global_only_once = 100
    self.groups = None
    self.prepped = False

  def try_line(self, line):
    """ Add a line, then return True if, given that line, a poem can be created."""
    self.add_line(line)
    return self.create_poem() #False or a poem.

  def take_out_of_fridge(self, pickle_file):
    jar = pickle.load( pickle_file )
    self.where_to_put_partial_lines = jar['where_to_put_partial_lines']
    self.rhyme_dict = jar['rhyme_dict']
    self.syllable_count_dict = jar['syllable_count_dict']
    self.groups = jar['groups']

  def put_in_fridge(self, pickle_file):
    if not self.groups:
      raise Exception, "Only put a poemifier in the fridge if you've run prep_for_creation()"
    jar = dict()
    jar['where_to_put_partial_lines'] = self.where_to_put_partial_lines
    jar['rhyme_dict'] = self.rhyme_dict
    jar['syllable_count_dict'] = self.syllable_count_dict
    jar['groups'] = self.groups
    pickle.dump( jar, open(pickle_file, 'wb') ) 

  def add_line(self, line):
    """
    Adds a line to the format hash dicts. Return False if the line cannot be used.
    """
    self.prepped = False
    #TODO: abstract away format stuff
    # format_items = [[self._rime, self.rhyme_dict], [self._syllable_count, self.syllable_count_dict]]
    # for hashFunc, format_hash_dict in format_items:
    splits = []

    for index, syllable_count_token in enumerate(self.format["syllable_structure"]):
      rest_of_syllables = self.format["syllable_structure"][index:] #inclusive
      temp_splits = line.split_line_to_format(rest_of_syllables)
      if temp_splits != False:
        splits += temp_splits
    #print splits

    for split in splits:
      if self.allow_partial_lines:
        for part_of_line in split:
          self._add_line_helper(part_of_line)
      else:
        #if partial lines aren't allowed, only add the first part of partial lines to the hashes; don't bother adding the rest.
        self._add_line_helper(split[0])
    return self._add_line_helper(line)

  def _add_line_helper(self, line):
    syll_count = line.syllable_count()
    if syll_count in self.format["syllable_count_to_syllable_count_token"].keys() or "any" in self.format["syllable_count_to_syllable_count_token"].keys() : #TODO: obviously, abstract this.
      rime = line.rime()
      if not rime:
        return False
      rime = tuple(rime)

      #TODO: DRY this out.
      for syll_count_token in self.format["syllable_count_to_syllable_count_token"].get(syll_count, []):
        if syll_count_token not in self.syllable_count_dict:
          self.syllable_count_dict[syll_count_token] = []
        self.syllable_count_dict[syll_count_token].append(line)

        if rime not in self.rhyme_dict:
          self.rhyme_dict[rime] = {}
        if syll_count_token not in self.rhyme_dict[rime]:
          self.rhyme_dict[rime][syll_count_token] = []
        self.rhyme_dict[rime][syll_count_token].append(line)
      if "any" in self.format["syllable_count_to_syllable_count_token"].keys():
        syll_count_token = syll_count
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

  def validate_rhyme(self, poem, line, index):
    """True if this line fits in the rhyme scheme where it is."""
    temp_poem = list(poem) #"copy" the list
    temp_poem[index] = line

    last_word = line.split(" ")[-1]
    last_word.strip(".,?!:;\" ")
    #does it fit where it is.
    rhyme_symbol = self.format["rhyme_scheme"][index]
    lines_to_compare_to = [temp_poem[i] for i, symbol in \
      enumerate(self.format["rhyme_scheme"]) if symbol == rhyme_symbol \
      and temp_poem[i] and i != index]
    if not lines_to_compare_to:
      if self.debug:
        print "nothing to compare " + last_word + " to. " 
      return True
    words_to_compare_to = map(lambda x: x.split(" ")[-1], lines_to_compare_to )
    return True in map(lambda x: self.rhyme_checker.rhymes_with(last_word, x), words_to_compare_to)

  def _group_lines_by_rime(self):
    """Group lines with the same syllable count and then by rime.

    all the lines in any of the dicts are guaranteed to be of acceptable length.
    e.g. groups = {6 => {"EH" => ["a", "b", "c"], "OI" => ...}, (9,11) => { "AH" => ["a", "b", "c"] "UH" => ...}, }
    """
    #print self.rhyme_dict[(('UW', 'L'),)]

    groups_by_rhyme = {}
    groups_by_syll_count = {}
    for rime, rhyme_groups in self.rhyme_dict.items():
      #skip rhyme dict entries with only one element, unless there are unrhyming elements in the rhyme scheme
      if len(rhyme_groups) == 1 and len(rhyme_groups.values()[0]) == 1 and \
          (self.allow_partial_lines or not rhyme_groups.values()[0][0].is_partial()) and \
            not filter(lambda item: self.format["rhyme_scheme"].count(item) == 1, list(self.format["rhyme_scheme"])):
        print "skipping %(l)s while grouping" % {'l' : rhyme_groups.values()[0]}
        continue
      inner_groups_by_syll_count = {}
      for syllable_count_token, rhyme_group in rhyme_groups.items():
        #exclude words from the rhyme group whose last word is the last word of another line in this rhyme group
        already_used_last_words = set()
        new_rhyme_group = []
        for rhyme_line in rhyme_group:
          last_word = rhyme_line.clean_text().split(" ")[-1].lower()
          if last_word not in already_used_last_words or \
            self.format["syllable_structure"].count(syllable_count_token) == 1:
            already_used_last_words.add(last_word)
            new_rhyme_group.append(rhyme_line)

        inner_groups_by_syll_count[syllable_count_token] = new_rhyme_group
        if syllable_count_token not in groups_by_syll_count.keys():
          groups_by_syll_count[syllable_count_token] = {}
        groups_by_syll_count[syllable_count_token][rime] = new_rhyme_group
      groups_by_rhyme[rime] = inner_groups_by_syll_count
    return groups_by_syll_count

  def _prune_too_small_grouped_lines(self, groups):
    """ Remove rimes with too few members, in place.

      The returned dict contains only lines that are eligible to appear in the poem.
      A rime_group has too few members iff:
        1. Its count of members is less than the maximum count of unique 
            elements in syllable structure or rhyme scheme.
    """

    min_rime_count = min(list(set(map(lambda x: self.format["rhyme_scheme"].count(x), self.format["rhyme_scheme"] ))))
    for syllcount, syllcount_group in groups.items():
      for rime, rime_group in syllcount_group.items():
        partials = sum([1 for l in rime_group if l.is_partial() and l.rime() == l.after_siblings()[0].rime() ])
        #TODO: only add partials that rime with their prev sibling (or is this necessary?)
        rime_group_effective_length = len(rime_group) + partials

        #conscious decision: not >=
        if rime_group_effective_length < max(self.format["syllable_structure"].count(syllcount), min_rime_count):
          del groups[syllcount][rime]
      if len(syllcount_group) == 0:
        del groups[syllcount]

  def _prune_desiblinged_lines_from_groups(self, groups):
    """filter out partial-lines whose siblings aren't in `groups`, in place"""

    #for each partial-line, figure out what order of syllable and rhyme structures would be needed to slot it into the poem
    #e.g. it's got two pieces that rhyme of 9-11 syllables each
    #remove those partial lines who can't fit anywhere. don't accept the partial line if it's picked where it can't fit.
    #slot in the partial line and everything after if it can.

    flat_list_of_kosher_lines = [lines for lines in groups.items()]
    for syllcount, syllcount_group in groups.items():
      #groups[syllcount] = {}
      for rime, rime_group in syllcount_group.items():
        for line in rime_group:
          if not line.is_partial():
            continue
          else:
            #TODO: abstract this bit.
            size = line.total_siblings() + 1 #+1 for the line itself.
            format_items = zip(self.format["rhyme_scheme"], self.format["syllable_structure"])
            sequential_format_orderings = [] 
            for i in range(0, (len(format_items) - size + 1)):
              sequential_format_orderings.append(format_items[i:i+size])
            okay = []

            for subformat in sequential_format_orderings:
              okay.append(True)
              mini_rhyme_rime_map = {} # 'a' => "EH" etc
              all_lines = [line] + line.after_siblings()


              for i, sibling_line in enumerate(all_lines):
                if not okay[-1]: #don't waste our time
                  continue

                rhyme_symbol = subformat[i][0]
                needed_syllable_count = subformat[i][1]
                #TODO: abstract this away.

                #test syllable count
                if isinstance(needed_syllable_count, int):
                  if sibling_line.syllable_count() != needed_syllable_count:
                    okay[-1] = False
                    #print "failed on syllable count " + str(needed_syllable_count)
                    break
                elif isinstance(needed_syllable_count, tuple):
                  if not (sibling_line.syllable_count() >= needed_syllable_count[0] and sibling_line.syllable_count() <= needed_syllable_count[1]):
                    okay[-1] = False
                    #print "failed on syllable count " + str(needed_syllable_count)
                    break
                elif needed_syllable_count == "any":
                  #its okay, no matter what
                  break

                #test rhyme
                if rhyme_symbol in mini_rhyme_rime_map:
                  #TODO: compare only the last N syllables in rime for N = min(len(rime1, rime2))
                  min_rime_size = min( len(mini_rhyme_rime_map[rhyme_symbol]), len(sibling_line.rime()))
                  if mini_rhyme_rime_map[rhyme_symbol][-min_rime_size:] != (sibling_line.rime()[-min_rime_size:],):
                    okay[-1] = False
                    #print "failed on rhyme: %(r1)s; %(r2)s" % {'r1': mini_rhyme_rime_map[rhyme_symbol][-min_rime_size:], 'r2':  (sibling_line.rime()[-min_rime_size],)}
                    break
                else:
                  mini_rhyme_rime_map[rhyme_symbol] = tuple(sibling_line.rime()) if sibling_line.rime() else False
                  if i == len(all_lines)-1:
                    okay[-1] = False

            if True not in okay:
              rime_group.remove(line)
            else:
              self.where_to_put_partial_lines[line] = [i for i, b in enumerate(okay) if b]
              #store where it's okay.

  def _shuffle_grouped_lines(self, groups):
    for syllcount, syllcount_group in groups.items():
      for rime, rime_group in syllcount_group.items():
        shuffle(rime_group)

  def prep_for_creation(self):
    """Do a bunch of prep work for creating a poem. Doesn't commit us to anything yet."""
    if self.prepped:
      return self.groups


    self.groups = self._group_lines_by_rime()
                        # seven = [item for sublist in self.groups[7].values() for item in sublist]
                        # print "seven: " + str([debug_line in seven for debug_line in debug_lines])
                        # print self.groups[7][(('AH', 'N'),)]

                        # flat_lines = [item.text for subl2 in [item for sublist in [d.values() for d in self.groups.values()] for item in sublist] for item in subl2]
                        # print [debug_line in flat_lines for debug_line in debug_lines]

    if self.verbose:
      for syllable_count in list(self.format["unique_syllable_structure"]):
        if syllable_count == "any":
          print "before pruning too small1, %(s)s: %(l)s" % {'s' : "total", 'l': str(len(self.groups))}
        print "before pruning too small1, %(s)s: %(l)s" % {'s' : syllable_count, 'l': str(len(self.groups.get(syllable_count, "")))}
    self._prune_too_small_grouped_lines(self.groups)
    if not self.allow_partial_lines:
      if self.verbose:
        for syllable_count in list(self.format["unique_syllable_structure"]):
          print "before pruning desiblinged, %(s)s: %(l)s" % {'s' : syllable_count, 'l': str(len(self.groups.get(syllable_count, "")))}
      self._prune_desiblinged_lines_from_groups(self.groups)
      if self.verbose:
        for syllable_count in list(self.format["unique_syllable_structure"]):
          print "before pruning too small2, %(s)s: %(l)s" % {'s' : syllable_count, 'l': str(len(self.groups.get(syllable_count, "")))}
      self._prune_too_small_grouped_lines(self.groups)
      if self.verbose:
        for syllable_count in list(self.format["unique_syllable_structure"]):
          print "after, %(s)s: %(l)s" % {'s' : syllable_count, 'l': len(self.groups.get(syllable_count, []))}
          print ""
    self.prepped = True
    return self.groups


  def create_poem(self, be_random=False):
    """ Return False or a poem. """
    #TODO: again, abstraction!
    groups = self.prep_for_creation()

    if not groups:
      if self.debug:
        print "no groups, that can't be right"
      return False

    poem = [None] * self.format["lines_needed"]
                        #old debug stuff: why is a haiku not being genreated?
                        # flat_lines = [item.text for subl2 in [item for sublist in [d.values() for d in self.rhyme_dict.values()] for item in sublist] for item in subl2]
                        # print [debug_line in flat_lines for debug_line in debug_lines]

    already_used_rimes = set()
    rimes_by_rhyme_element = {}
    unique_rhyme_scheme = set(list(self.format["rhyme_scheme"]))
    for rhyme_element in unique_rhyme_scheme:
      unique_syllable_structure = list(self.format["unique_syllable_structure"])
      shuffle(unique_syllable_structure)
      for syllable_count_token in unique_syllable_structure:
        if syllable_count_token not in groups and syllable_count_token != "any":
          continue

        if syllable_count_token == "any":
          candidate_lines = choice(groups.values()).values()
        else:
          candidate_lines = groups[syllable_count_token].values()
        if be_random:
          shuffle(candidate_lines)

        # print "candidate lines: %(c)s" % {'c' : candidate_lines}

        if not candidate_lines:
          continue

        #for each syllable in the candidate lines for this syllable_count_token, create a poem
        for this_sylls_lines in candidate_lines:
          for index, syllable_count in enumerate(self.format["syllable_structure"]):
            if syllable_count == syllable_count_token and rhyme_element == self.format["rhyme_scheme"][index]:
              for next_line in this_sylls_lines:

                #ensures that 'a' and 'b' elements don't rhyme with each other (so it doesn't end up being aaaa for aabb)
                if next_line.rime() not in already_used_rimes or next_line.rime() in rimes_by_rhyme_element.get(rhyme_element, set()):
                  already_used_rimes.add(next_line.rime())
                  if rhyme_element not in rimes_by_rhyme_element:
                    rimes_by_rhyme_element[rhyme_element] = set()
                  rimes_by_rhyme_element[rhyme_element].add(next_line.rime())


                  if not poem[index] and next_line not in poem: #ensures there are no duplicate lines in poems.
                    if (not self.allow_partial_lines) and next_line.is_partial():
                      if next_line in self.where_to_put_partial_lines:
                        if index in self.where_to_put_partial_lines[next_line]:
                          if self.verbose:
                            print "line %(i)s (%(l)s) is partial and acceptable" %{'i': index , 'l': next_line}
                          poem[index] = next_line
                          for j, sibling in enumerate(next_line.after_siblings()):
                            #these can be depended on to fit the right syllable structure, but not rhyme. #TODO
                            poem[j + 1 + index] = sibling
                            # print "slotted in a sibling to line #%(i)s" % {'i': j + index}
                      #   else:
                      #     print "line %(l)s doesn't fit in line %(n)s" % {'l' : next_line, 'n' : index}
                      # else:
                      #   if next_line.text != "":
                      #     print str(next_line) + " didn't make it"
                    else:
                      # print "line " + str(index) + " partial? " + str(next_line.is_partial())
                      poem[index] = next_line
                      continue
                  # else:
                  #   if poem[index]:
                  #     print "skipping because line is already filled"
                  #   if next_line in poem: 
                  #     print "skipping because next_line already in poem"
                  #   print ""
            # else:
            #   pass
              # print "skipped %(l)s due to syllable/rhyme problems" % {'l' : this_sylls_lines}
              # print "syllable_count: %(sc)s , syllable_count_token: %(sct)s" % {'sc': syllable_count, 'sct': syllable_count_token}
              # print "rhyme_element: %(sc)s , self.format[rhyme_scheme][index]: %(sct)s" % {'sc': rhyme_element, 'sct': self.format["rhyme_scheme"][index]}
              # print ""
    # if not self.allow_partial_lines:
    #   print "generated " + str(len(poems)) + " semivalid poems"
    #   poems = self._cull_desiblinged_lines_from_poems(poems)
    #print "generated " + str(len(poems)) + " valid poems"
    if None in poem:
      return False
    else:
      return poem

def _test():
  import doctest
  doctest.testmod()

class ShitsFuckedException(Exception):
  pass


def poem_ex_nihilo(**kwargs):
  if 'format' in kwargs:
    poem = getattr(poemformat, kwargs['format'].capitalize())() #class
  else:
    poem = getattr(poemformat, sys.argv[1].capitalize())() #class

  if 'input_text' in kwargs:
    input_text = './SCALIA.txt'
  else:
    input_text = sys.argv[2] or "./SCALIA.txt"

  text = open(input_text).read()
  sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
  linetexts = sent_detector.tokenize(text)

  # lists_of_linetexts = map(lambda x: x.split(";"), open(input_text).read().split("\n"))
  # #lists_of_linetexts = map(lambda x: x.split(","), open(sys.argv[2]).read().split("\n"))

  # linetexts = [line for line_list in lists_of_linetexts for line in line_list]

  #linetexts = ["camping is in tents", "my tree table tries", "between those times I slept none"]
  # linetexts = ["many words in english rhyme with song", "one two three four five six", "a bee see dee word kicks",
  #  "This is a line that is twenty long", "here are ten more ending in wrong", "Jeremy Bee Merrill plays ping pong",
  #  ]
  if 'rhyme_checker' in kwargs:
    p = Poemifier(poem, rhyme_checker=kwargs['rhyme_checker'])
  else:
    p = Poemifier(poem)
  p.debug = True
  p.verbose = kwargs.get('verbose', False)
  p.allow_partial_lines = kwargs.get('allow_partial_lines', False)
  #this can't be a do... while, because we have to add all the lines, then do various processing steps.
  for linetext in linetexts:
    print linetext
    line = Line(linetext, p.rhyme_checker)
    if line.should_be_skipped():
      continue
    #p.try_line(line) #too slow
    p.add_line(line)
  print ""
  complete_poem = p.create_poem(kwargs.get('be_random', True))
  if complete_poem:
    print poem.format_poem( complete_poem ) #random?
  else:
    print "No Poem"

def profile():
  #N.B. these don't, work, jus tcopy/paste them into the if name = main block
  import cProfile
  import pstats
  cProfile.run("poem_ex_nihilo(format='haiku', input_text=None, be_random=False)", 'binaryprofile.prof', 'tottime')
  pstats.Stats('binaryprofile.prof').sort_stats('tottime').print_stats(.1)

def profile_without_initializing_rhymechecker():
  #N.B. these don't, work, jus tcopy/paste them into the if name = main block
  import cProfile
  import pstats
  r = RhymeChecker()
  cProfile.run("poem_ex_nihilo(rhyme_checker=r, format='haiku', input_text=None, be_random=False)", 'binaryprofile.prof', 'tottime')
  pstats.Stats('binaryprofile.prof').sort_stats('tottime').print_stats(.1)

if __name__ == "__main__":
  poem_ex_nihilo(be_random=True, verbose=True, allow_partial_lines=True)
#TODO: write tests (i.e. with randomness off)
#TODO: reverse arguments to allow additional stuff to be specified on command line. or is this stupid, since I'm gonna put it on AWS?
#TODO: Allow multiple poems to be requested (only break when the number of complete poems in self.poems = the number requested)
#TODO: use espeak, add pitch to "sing" the poems

