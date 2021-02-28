# What is death lessons?

Death lessions makes preventing future death reports searchable. In the UK, when in the course of investigating a death coroners are concerned that the circumstances giving rise to the death may occur again, and could be prevented, they have a legal duty to complete a "Preventing Future Death" report. PFD reports are sent to the chief coroner and published [online](https://www.judiciary.uk/subject/prevention-of-future-deaths/) so that lessons can be learned.

Prior to [deathlessons.org](http://deathlessons.org) PFD reports were not easily searchable because they are published as PDFs. One could not, for example, readily find all PFD reports mentioning [asthma](http://deathlessons.org/?q=Asthma). Now you can.

# Technical Notes

## Deploying the HTML

```
rsync -av --rsync-path="sudo rsync"  server/app/index.html  ubuntu@deathlessons.org:/var/www/html/
```

## Re-indexing

```
sudo systemctl restart tantiivy.service
```


## TODO

* show only relevant snippet from the search (tom)
* find prior art for design / style (Carl) - we should make search box more obvious to find e.g https://uxplanet.org/design-a-perfect-search-box-b6baaf9599c
* link should not be its own column (tom)
* remove "show 10 rows" (tom)
* disable caching completely (tom)
