import xml.etree.ElementTree as ET
import re
import sys
import os
import pyperclip
from pathlib import Path
from subprocess import call

###########################################################################
# This script extracts "layers" for usage in LaTeX presentations          #
# from inkscape SVG files. For this, append a LaTeX overlay specification #
# to the label of the layer, e.g., "1,2-5,3,17-", which you surround by   #
# either angle or square brackets. Then, call this script with the name   #
# of the SVG file as argument (works also with a path). It will export    #
# multiple PDF files "...-step-N.pdf" in the same directory as the SVG    #
# file. After execution, the script shows instructions of how to use the  #
# generated PDF animation slides in LaTeX and copies the for loop doing   #
# the task to the system clipboard.                                       #
#                                                                         #
# Requirements:                                                           #
# - inkscape                                                              #
# - pyperclip library ("pip3 install pyperclip")                          #
###########################################################################

ns = {'svg': 'http://www.w3.org/2000/svg',
      'inkscape': 'http://www.inkscape.org/namespaces/inkscape'}

class OverlayRange:
    def __init__(self, start, end):
        self.start = int(start)
        self.end = int(end)

    def __str__(self):
        if (self.end == -1):
            return "range(" + str(self.start) + "-" + ")"
        else:
            return "range(" + str(self.start) + "-" + str(self.end) + ")"

    def max(self):
        if (self.end > self.start):
            return self.end
        else:
            return self.start

    def setMax(self, max):
        if (self.end == -1):
            self.end = max

    def visibleAt(self, step):
        return (self.start <= step and step <= self.end)

    @classmethod
    def fromStartOnly(cls, start):
        return cls(start, -1)

def parseOverlayRange(string):
    arr = string.split('-')
    if (len(arr) == 1):
        return OverlayRange(arr[0], arr[0])
    elif (len(arr) == 2 and arr[1] == ''):
        return OverlayRange.fromStartOnly(arr[0])
    elif (len(arr) == 2):
        return OverlayRange(arr[0], arr[1])

class Layer:
    def __init__(self, label, element):
        self.label = label
        self.element = element
        self.ranges = []

    def addRange(self, therange):
        self.ranges.append(therange)

    def maxRange(self):
        return max(map(lambda r: r.max(), self.ranges))

    def visibleAt(self, step):
        for therange in self.ranges:
            if (therange.visibleAt(step)):
                return True
        return False

def toNS(elem, namespace):
    return '{' + ns.get(namespace) + '}' + elem

if (len(sys.argv) < 2):
    print('Expecting input SVG file as argument')

inputfile = sys.argv[1]
outprefix = inputfile.split('.svg')[0]

tree = ET.parse(inputfile)
root = tree.getroot()

layers = []

for elem in tree.iter():
    if (elem.tag != toNS('g', 'svg')):
        continue

    label = elem.get(toNS('label', 'inkscape'))
    if (label == None):
        continue

    groupmode = elem.get(toNS('groupmode', 'inkscape'))
    if (groupmode == None or groupmode != 'layer'):
        continue

    regex = r"^([^(<\[)]*)\W+(?:<|\[)([0-9]+(?:-(?:[0-9]+)?)?(?:,[0-9]+(?:-(?:[0-9]+)?)?)*)(?:>|\])$"
    m = re.search(regex, label)
    if (m == None):
        continue

    layer = Layer(m.group(1), elem)
    for theRange in m.group(2).split(','):
        layer.addRange(parseOverlayRange(theRange))

    layers.append(layer)

maxLayer = max(map(lambda l: l.maxRange(), layers))

print("Maximum overlay number: " + str(maxLayer))

for layer in layers:
    for therange in layer.ranges:
        therange.setMax(maxLayer)

for i in range(1,maxLayer+1):
    print("Animation step " + str(i))
    for layer in layers:
        if (layer.visibleAt(i)):
            print ("  Layer " + layer.label + " visible")
            layer.element.set('style', 'display:inline')
        elif (not layer.visibleAt(i)):
            print ("  Layer " + layer.label + " hidden")
            layer.element.set('style', 'display:none')

    layerOutPrefix = outprefix + '-step-' + str(i)
    svgoutfile = layerOutPrefix + '.svg'
    pdfoutfile = layerOutPrefix + '.pdf'

    if Path(svgoutfile).exists():
        print("Step SVG file " + svgoutfile + " already exists, won't override but cancel")
        quit()

    print("  Exporting layer " + str(i) + " to file " + pdfoutfile)
    tree.write(svgoutfile)
    call(['inkscape', '-z', '-C', '--export-filename=' + pdfoutfile, svgoutfile])

    os.remove(svgoutfile)

latexinclude = "    \\usepackage{pgffor}\n" +\
               "    \\usepackage{tikz}"
latexMacro = "    \\newcommand<>{\\fullsizegraphic}[1]{\n" +\
             "      \\begin{tikzpicture}[remember picture,overlay]\n" +\
             "        \\node[at=(current page.center)] {\n" +\
             "          \includegraphics{#1}\n" +\
             "        };\n" +\
             "      \\end{tikzpicture}\n" +\
             "    }"
latexForLoop = "    \\foreach \\n in {1,...," + str(maxLayer) + "}{\n" +\
               "        \\only<\\n>{\\fullsizegraphic{" + outprefix + "-step-\\n.pdf}}\n" +\
               "    }"

print("\nDone. Usage in Latex:")
print("  Include in preamble:\n")
print(latexinclude)
print("")
print(latexMacro)
print("\n  Use in frame:\n")
print(latexForLoop)

pyperclip.copy(latexForLoop)
print("\nCopied for loop to clipboard.")