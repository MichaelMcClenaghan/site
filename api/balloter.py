# -*- coding: utf-8 -*-

import cPickle
import cStringIO
import string

from flask import Flask, abort, make_response, request

from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

app = Flask(__name__)

DISCLAIMER_TEXT = "This is a custom-generated voting reference not under " \
                  "any circumstances to be distributed or used as how to " \
                  "vote material.  For more information please visit " \
                  "http://belowtheline.org.au/"
LOGO_FILENAME = 'belowtheline-print.png'

FONT = 'Helvetica'
A4R = landscape(A4)
font = pdfmetrics.getFont(FONT)

PAGE_HEIGHT = A4R[1]
PAGE_WIDTH = A4R[0]

TOP_MARGIN = 10 * mm
BOTTOM_MARGIN = 6.5 * mm
LEFT_MARGIN = 6.5 * mm
RIGHT_MARGIN = 6.5 * mm

GROUP_ROW_GAP = 5 * mm

BOX_SIZE = 6 * mm
BOX_GAP = 5.25 * mm

FONT_SIZE = 8.0
CANDIDATE_FONT_SIZE = 7.5
PARTY_FONT_SIZE = 5.0

GROUPS_PER_ROW = 8

GROUP_WIDTH = (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN) / GROUPS_PER_ROW
LABEL_WIDTH = GROUP_WIDTH - BOX_SIZE - 6 * mm

ballots = cPickle.load(open('ballots.pck'))

def disclaimer(c):
    c.drawString(10 * mm, PAGE_HEIGHT - 6 * mm, DISCLAIMER_TEXT)

def end_page(c):
    disclaimer(c)
    c.showPage()
    c.setFont(FONT, FONT_SIZE)

def draw_candidate(c, number, family, given, party, i, tl, br):
    number = str(number)

    c.rect(tl[0] + 1 * mm,
           tl[1] - 3 * mm - i * BOX_GAP - (i + 1) * BOX_SIZE,
           BOX_SIZE, BOX_SIZE)
    width = font.stringWidth(number, FONT_SIZE + 1.0)
    c.setFont(FONT, FONT_SIZE + 1.0)
    c.drawCentredString(tl[0] + 1.1 * mm + BOX_SIZE / 2.0,
                        tl[1] - 2.3 * mm - i * BOX_GAP - (i + 1) * BOX_SIZE + 1.5 * mm,
                        number)
    text = c.beginText(tl[0] + 2 * mm + BOX_SIZE,
                       tl[1] - 3 * mm - i * BOX_GAP - i * BOX_SIZE - 4.5)
    text.setFont(FONT + '-Bold', CANDIDATE_FONT_SIZE,
                 leading=1.1 * CANDIDATE_FONT_SIZE)
    text.textLine(family)
    text.setFont(FONT, CANDIDATE_FONT_SIZE,
                 leading=CANDIDATE_FONT_SIZE)
    text.textLine(given)
    if party:
        party = party.upper()
        text.setFont(FONT, PARTY_FONT_SIZE)
        if font.stringWidth(party, PARTY_FONT_SIZE) > LABEL_WIDTH:
            bits = party.split(' ')
            for i in range(len(bits) - 1, 0, -1):
                s = ' '.join(bits[:i])
                if font.stringWidth(s, PARTY_FONT_SIZE) <= LABEL_WIDTH:
                    text.textLine(s)
                    text.textLine(' '.join(bits[i:]))
                    break
        else:
            text.textLine(party.upper())
    c.drawText(text)

    c.setFont(FONT, FONT_SIZE)

def generate(division, div_ticket, state, sen_ticket):
    container = cStringIO.StringIO()
    c = canvas.Canvas(container, A4R)
    c.setLineWidth(0.1)
    c.setStrokeColor(black)
    c.setFont(FONT, FONT_SIZE)

    groups = ballots[state]
    division_name, candidates = ballots[division]
    row = 0
    col = 0

    division_height = len(candidates) * (BOX_SIZE + BOX_GAP) + BOX_GAP
    tl = (LEFT_MARGIN + col * GROUP_WIDTH, PAGE_HEIGHT - TOP_MARGIN)
    br = (tl[0] + GROUP_WIDTH, tl[1] - division_height)

    width = font.stringWidth(division_name, FONT_SIZE)
    offset = (GROUP_WIDTH - width) / 2

    c.setFillColorRGB(0.8745, 0.94117, 0.84705)
    c.rect(tl[0], br[1], GROUP_WIDTH, division_height, fill=1)
    c.setFillColor(black)

    for i in range(0, len(candidates)):
        family, given, party = candidates[i]
        number = div_ticket.pop(0)
        draw_candidate(c, number, family, given, party, i, tl, br)

    row_height = PAGE_HEIGHT - TOP_MARGIN
    first_page = True

    def group_block_iterator(groups):
        index = 0
        height = PAGE_HEIGHT - TOP_MARGIN - division_height - BOX_GAP
        while first_page and row_height >= height and index < len(groups):
            yield 2, groups[index:index + GROUPS_PER_ROW - 2]
            index += GROUPS_PER_ROW - 2
        for block in range(index, len(groups), GROUPS_PER_ROW):
            yield 0, groups[block:block + GROUPS_PER_ROW]

    for col_offset, block in group_block_iterator(groups):
        max_candidates = max([len(g['candidates']) for g in block])
        group_height = max_candidates * (BOX_SIZE + BOX_GAP) + BOX_GAP
        tl = None
        br = None

        for col, group in enumerate(block):
            col += col_offset

            if row_height <= group_height + GROUP_ROW_GAP:
                first_page = False
                end_page(c)
                row_height = PAGE_HEIGHT - TOP_MARGIN

            if group['label'] != 'UG':
                group_label = "Group " + group['label']
            else:
                group_label = 'Ungrouped'

            width = font.stringWidth(group_label, FONT_SIZE)
            offset = (GROUP_WIDTH - width) / 2

            tl = (LEFT_MARGIN + col * GROUP_WIDTH, row_height)
            br = (tl[0] + GROUP_WIDTH, tl[1] - group_height)

            c.drawString(tl[0] + offset, tl[1] - mm, group_label)
            c.line(tl[0] + offset - 0.5 * mm, tl[1], tl[0], tl[1])
            c.line(tl[0], tl[1], tl[0], br[1])
            c.line(tl[0], br[1], br[0], br[1])
            c.line(br[0], tl[1], tl[0] + offset + width + 0.5 * mm, tl[1])

            col += 1

            for i in range(0, len(group['candidates'])):
                family, given, party = group['candidates'][i]
                number = sen_ticket.pop(0)
                draw_candidate(c, number, family, given, party, i, tl, br)

        c.line(br[0], br[1], br[0], tl[1])
        row_height -= group_height + GROUP_ROW_GAP

    disclaimer(c)
    c.save()

    return container.getvalue()

@app.route('/pdf', methods=['POST'])
def pdf():
    division_ticket = request.form['division_ticket'].split(',')
    senate_ticket = request.form['senate_ticket'].split(',')
    pdf = generate(request.form['division'], division_ticket,
                   request.form['state'], senate_ticket)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'filename=ballot.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
    # import sys
    # open('test.pdf', 'w').write(generate(sys.argv[1], range(1, 20),
    #                                      sys.argv[2], range(1, 200)))