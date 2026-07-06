import {defineField, defineType} from 'sanity'

const DEVICES = [
  {title: 'Hidden word', value: 'Hidden word'},
  {title: 'Anagram', value: 'Anagram'},
  {title: 'Reversal', value: 'Reversal'},
  {title: 'Charade', value: 'Charade'},
  {title: 'Container', value: 'Container'},
  {title: 'Double definition', value: 'Double definition'},
]

export const puzzlePart = defineType({
  name: 'puzzlePart',
  title: 'Clue part',
  type: 'object',
  fields: [
    defineField({name: 'text', title: 'Text', type: 'string', validation: (r) => r.required()}),
    defineField({
      name: 'role',
      title: 'Role',
      type: 'string',
      options: {
        list: [
          {title: 'Definition (def)', value: 'def'},
          {title: 'Indicator / 2nd definition (ind)', value: 'ind'},
          {title: 'Plain', value: ''},
        ],
      },
    }),
  ],
  preview: {
    select: {title: 'text', subtitle: 'role'},
    prepare({title, subtitle}) {
      return {title, subtitle: subtitle || '(plain)'}
    },
  },
})

export const puzzleClue = defineType({
  name: 'puzzleClue',
  title: 'Clue',
  type: 'object',
  fields: [
    defineField({
      name: 'answer',
      title: 'Answer',
      type: 'string',
      validation: (r) => r.required().uppercase().regex(/^[A-Z]+$/, {name: 'letters only'}),
    }),
    defineField({
      name: 'device',
      title: 'Device',
      type: 'string',
      options: {list: DEVICES},
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'parts',
      title: 'Parts',
      description: 'The clue surface, split into [text, role] spans. Concatenated in order, they must read as the full clue including the enumeration, e.g. " (5)".',
      type: 'array',
      of: [{type: 'puzzlePart'}],
      validation: (r) => r.required().min(1),
    }),
    defineField({
      name: 'parse',
      title: 'Parse (shown after solving)',
      type: 'text',
      rows: 2,
      validation: (r) => r.required(),
    }),
  ],
  preview: {
    select: {answer: 'answer', device: 'device'},
    prepare({answer, device}) {
      return {title: answer, subtitle: device}
    },
  },
})

export const puzzle = defineType({
  name: 'puzzle',
  title: 'Puzzle',
  type: 'document',
  fields: [
    defineField({
      name: 'number',
      title: 'Number',
      type: 'number',
      validation: (r) => r.required().integer().positive(),
    }),
    defineField({
      name: 'date',
      title: 'Release date',
      description: 'Rolls over at midnight Europe/London time.',
      type: 'date',
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'link',
      title: 'Link',
      type: 'string',
      validation: (r) => r.required().uppercase(),
    }),
    defineField({
      name: 'linkType',
      title: 'Link type',
      type: 'string',
      options: {
        list: [
          {title: 'Compound', value: 'compound'},
          {title: 'Category', value: 'category'},
        ],
      },
      initialValue: 'compound',
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'compounds',
      title: 'Display line',
      description: 'e.g. "CAMPFIRE · SUREFIRE · SPITFIRE · CEASEFIRE · CROSSFIRE"',
      type: 'string',
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'note',
      title: "Setter's note",
      description: 'Shown on the solution page once the puzzle is retired to the archive.',
      type: 'text',
      rows: 3,
    }),
    defineField({
      name: 'clues',
      title: 'Clues',
      type: 'array',
      of: [{type: 'puzzleClue'}],
      validation: (r) => r.required().min(4).max(5),
    }),
  ],
  preview: {
    select: {number: 'number', link: 'link', date: 'date'},
    prepare({number, link, date}) {
      return {title: `No. ${number} — ${link}`, subtitle: date}
    },
  },
})
