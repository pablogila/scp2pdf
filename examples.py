import scp2pdf


# We can compile a single entry with custom options:

scp2pdf.generate(
    target="173",
    theme="report",
    image="https://upload.wikimedia.org/wikipedia/commons/c/c7/MatthewF1.png",
    caption="Artistic depiction of SCP-173 by ThyCheshireCat",
    outdir="./examples"
)


# We can also compile multiple custom entries with a loop:

elements_to_compile = [
    {
        'target': 173,
        'theme': 'report',
        'image': 'https://upload.wikimedia.org/wikipedia/commons/c/c7/MatthewF1.png',
        'caption': 'Artistic depiction of SCP-173 by ThyCheshireCat',
        'outdir': './examples',
    },{
        'target': 35,
        'outdir': './examples',
    },{
        'target': '682',
        'outdir': './examples',
    },{
        'target': 2207,
        'image': 'pictures/SCP-2207.jpg',
        'caption': 'Device as stored on Site-██',
        'outdir': './examples',
    },{
        'target': 2521,
        'outdir': './examples',
    },{
        'target': 'https://scp-wiki.wikidot.com/survey-log-1165',
        'outdir': './examples',
    },{
        'target': 6003,
        'outdir': './examples',
    },{
        'target': 6281,
        'theme': 'book',
        'outdir': './examples',
    },{
        'target': '603',
        'theme': 'book',
        'outdir': './examples',
    }
]

for element in elements_to_compile:
    scp2pdf.generate(**element)

