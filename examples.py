import scp2pdf


# We can compile a single entry with custom options:

scp2pdf.generate(
    target="35",
    outdir="./examples",
    theme="report",
)


# We can also compile multiple custom entries with a loop:

elements_to_compile = [
    {
        'target': '173',
        'image': "https://upload.wikimedia.org/wikipedia/commons/c/c7/MatthewF1.png",
        'caption': "Artistic depiction of SCP-173 by ThyCheshireCat",
        'outdir': './examples',
        'theme': 'book',
    },{
        'target': '603',
        'outdir': './examples',
        'theme': 'scan',
    },{
        'target': '682',
        'outdir': './examples',
        'theme': 'badscan',
    },{
        'target': 2207,
        'image': 'pictures/SCP-2207.jpg',
        'caption': 'Device as contained on Site-██',
        'outdir': './examples',
        'theme': 'wrinkled',
    },{
        'target': 'https://scp-wiki.wikidot.com/survey-log-1165',
        'outdir': './examples',
        'theme': 'shredded',
    }
]

for element in elements_to_compile:
    scp2pdf.generate(**element)

