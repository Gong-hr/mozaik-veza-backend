# Mozaik veza

## O projektu

Mozaik veza je alat koji omogućuje istraživačkim novinarima, aktivistima i zainteresiranoj javnosti istraživanje
međusobnih veza politički izloženih osoba, kao i veza s drugim pravnim i fizički osobama, na temelju podataka preuzetih
iz registara i baza javnih tijela. Mozaik veza omogućuje pretragu, filtriranje i vizualizaciju traženih podataka uz
korištenje naprednih softverskih alata.

## Tehnički preduvijeti

Mozaik veza je Django aplikacija.

- Linux
- Python 3.5 ili više
- PostgreSQL
- Elasticsearch (>= 6.0.0, < 7.0.0)
- Neo4j
- Redis
- Docker (opcionalno)

## Instalacija

```bash
apt-get install -y git python3 python3-venv
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
mkdir moc
cd moc
python3 -m venv .virtualenv
source .virtualenv/bin/activate
git clone https://github.com/Gong-hr/mozaik-veza-backend.git moc
cd moc
pip install wheel
pip install --upgrade -r requirements.txt
```

## Konfiguracija

Konfiguracijska datoteka je `moc/settings.py`.

## Inicijalizacija

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata init_data.json
python manage.py loaddata migration_0005_data.json
python manage.py loaddata importer_group_data.json
python manage.py loaddata savings.json
python manage.py reindex-elasticsearch --init-entities --entities
python manage.py reindex-elasticsearch --init-attributes --attributes
python manage.py reindex-elasticsearch --init-connection-types --connection-types
python manage.py reindex-elasticsearch --init-attribute-values-log --attribute-values-log
python manage.py reindex-elasticsearch --init-entity-entity-log --entity-entity-log
python manage.py reindex-elasticsearch --init-codebook-values --codebook-values
python manage.py build-graph-neo4j --init-entities --entities
```

### Workers

```bash
python manage.py rqworker db
python manage.py rqworker elasticsearch
python manage.py rqworker neo4j
python manage.py rqworker notification_mails
python manage.py rqworker system_mails
python manage.py rqscheduler --queue scheduler
```

### Aplikacija

#### Razvoj

```bash
python manage.py runserver 0.0.0.0:8000
```

#### Produkacija

```bash
gunicorn --bind=0.0.0.0:8000 --timeout=300 --workers=9 --name=mocbackend moc.wsgi
```

### Cron poslovi

```bash
python manage.py cron --schedule find_updated_entities_and_send_mail
python manage.py cron --schedule update_dbs
```

## Struktura podataka i poslovna logika

### Entiteti i veze

U sustavu postoje dvije osnovne vrste objekata: ***entiteti*** i ***veze***. Svaki entitet je nekog ***tipa*** (npr.
pravna osoba, fizička osoba, nekretnina, pokretnina, itd.). Dva entiteta mogu biti povezana ***vezom***. Svaka veza je
nekog ***tipa*** (npr. "zaposlen u").

Predefinirani tipovi entiteta su:

- *person* - fizička osoba
- *legal_entity* - pravna osoba
- *real_estate* - nekretnina
- *movable* - pokretnina
- *savings* - štednja

### Izvori i kolekcije

Za svaku informaciju u sustavu, mora se znati od kuda je došla. Izvor reprezentira npr. neko državno
tijelo, dok kolekcija reprezentira neku kolekciju podataka unutar izvora.

### Tvrdo i meko brisanje, objavljivanje

Svaki podatak u sustavu moguće je *meko* obrisati. To znači da sam podatak nije obrisan već je samo označen kao obrisan.
Slično tome, svaki podatak može biti objavljen ili neobjavljen. Podatak je vidljiv ako nije *meko* obrisan i ako je
objavljen.

### Kada je entitet ***PEP (politically exposed person)***

Svaki entitet ima informaciju da li su entiteti povezani sa njim potencijalni PEP-ovi. Također
svaki tip veze ima informaciju da li su entiteti povezani sa vezom danog tipa potencijalni PEP-ovi.
Entitet je PEP kada je povezan sa entitetom koji ima informaciju da su povezani entiteti sa njim potencijalni PEP-ovi
vezom čiji tip veze ima informaciju da su entiteti povezani tim tipom veze potencijalni PEP-ovi.

Npr. Entitet Hrvatski sabor ima informaciju da su entiteti povezani sa njim potencijalni PEP-ovi. Tip veze "kuhar"
nema informaciju da su entiteti povezani tim tipom veze potencijalni PEP-ovi, tako da kuhar u Hrvatskom saboru nije PEP.
Sa druge strane tip veze "predsjednik" ima informaciju da su entiteti povezanim tim tipom veze potencijalni PEP-ovi, pa
je predsjednik Hrvatskog sabora PEP.

Nadalje, svaka fizička osoba povezana sa PEP-om je PEP.

### Atributi i vrijednosti atributa

Postoje dvije vrste atributa: *osnovni atributi* i *dodatni atributi* entiteta i veza.

Osnovni atributi entiteta su:

- *public_id* - jedinstveni identifikator entiteta
- *linked_potentially_pep* - govori o tome je li povezani potencijalno ***PEP***
- *force_pep* - ako je *true* onda je dani entitet ***PEP***
- *published* - govori je li dani entitet objavljen
- *deleted* - govori o tome je li dani entitet obrisan

Predefinirani dodatni atributi entiteta:

- *person_first_name* - ime fizičke osobe
- *person_last_name* - prezime fizičke osobe
- *legal_entity_name* - ime pravne osobe
- *legal_entity_entity_type* - tip pravne osobe
- *person_vat_number* - OIB fizičke osobe
- *legal_entity_vat_number* - OIB pravne osobe
- *real_estate_name* - ime nekretnine
- *movable_name* - ime pokretnine

Osnovni atributi veze su:

- *connection_type* - tip veze
- *entity_a*, *entity_b* - krajevi (entiteti) veze
- *transaction_amount* - iznos, ako se radi o transakcijskoj vezi
- *transaction_currency* - valuta, ako se radi o transakcijskoj vezi
- *transaction_date*, datum transakcije, ako se radi o transakcijskoj vezi
- *valid_from*, *valid_to* - vremenski period kada je trajala veza
- *published* - govori je li dani entitet objavljen
- *deleted* - govori o tome je li dani entitet obrisan

Atributi: *connection_type*, *entity_a*, *entity_b*, *transaction_amount*, *transaction_currency*, *transaction_date*,
*valid_from*, *valid_to* su jedinstveni.

Vrijednost atributa je bilo koja informacija koja opisuje ***entitet*** ili ***vezu***. Da bi smo mogli ***entitetu***
ili ***vezi*** dodijeliti vrijednost atributa, prvo se mora definirati atribut. Za ***entitete*** atributi se definiraju
za ***tip entiteta***, a za ***veze*** atributi se definiraju za ***kolekcije***.

#### Kompleksni atributi

Kompleksni atributi su specijalna vrsta atributa za koje se ***entitetima*** i ***vezema*** ne mogu dodijeliti
vrijednosti, već njima možemo dodijeliti druge atribute (komplesne i nekompleksne). Komplesnim atributima možemo
odvojiti neke atribute u logičku cjelinu. Npr. *kredit* može biti kompleksan atribut, a trajanje kredita, visina
kredita, kamatna stopa su njegovi podatributi.

### Log

Sve promjene na atributima (entiteta ili veza), kao i na samim vezama se spremaju u log. Zapis u log-u za vrijednost
atributa ima slijedeće informacije:

- *vrijeme* - vrijeme promijene
- *kolekcija* - iz koje je kolekcije promjena došla
- *entitet* ili *veza* - nad kojim entitetom ili vezom se napravila promjena
- *atribut* - vrijednost kojeg atributa je promjenjena
- *stara vrijednost*
- *nova vrijednost*

Zapis u log-u za veze ima slijedeće informacije:

- *vrijeme* - vrijeme promijene
- *kolekcija* - iz koje je kolekcije promjena došla
- *veza* - nad kojim entitetom ili vezom se napravila promjena
- *novo trajanje veze*
- *staro trajanje veze*

### Ostala poslovna logika

####  Kreiranje entiteta

Pri kreiranju entiteta potrebno je ime entiteta, a opcionalna polja su prezime i oib. Ove informacije služe za kreiranje
*public_id*-a entiteta i provjeru da li entitet već postoji u bazi. Također je moguće postiviti i zastavicu
*force_creation*. Upisom entiteta ne upisuju se vrijednosti za ime (i prezime) i oib, već ih je potrebno unjeti kao
vrijednosti atributa. 

#### Kreiranje veza

Pri kreiranju veza provjerava se da li slična veza već postoji u bazi. Također je moguće napraviti ažuriranje postojeće
veze ako se specificira *id* postojeće veze. Također, moguće je postaviti zastavicu *force_creation*.

## Baze podataka

### PostgreSQL

Ova baza podataka služi kao "master" spremište podataka. Iz nje se dalje podaci šalju u druge baze podataka.

### Elasticsearch

Ova baza podataka služi za indeksiranje većine podataka koje se nalaze u relacijskoj bazi podataka.

### Neo4j

Ova baza služi za indeksiranje entiteta i veza, tj. grafa.

### Redis

Ova baza podataka služi kao backend za *django-rq*.

## API

Za interakciju sa bazom API. API je dostupan na:

`https://.../api/`

Dokumentacija API-ja je dostupna na:

`https://.../api/docs/`

Schema API-ja je dostupna na:

`https://.../api/schema/`

Dio API-ja je javan (čitanje podataka iz baza), dok je dio API-ja je zatvoren (upis podataka u bazu).
Kako bi korisnik mogao upisivati kroz API, potrebno ga je staviti u grupu *importer*. Nakon toga korisnik može
dobiti token preko:

`http://.../api/api-token-auth/`

Da bi se token koristio potrebno je dodati *auth_token=\<TOKEN\>* kao GET argument requesta.

API za dohvat podataka iz Elasticsearch-a je dostupan na:

`http://.../api/search/...`

API za dohvat podataka iz Neo4j-a je dostupan na:

`http://.../api/graph/...`

### Key-Value skladište

Kao dodatak, sustav ima i permanentno *key-value* spremište podataka, gdje je key (uređena) lista string-ova, a value
string. Key-Value spremište je dostupno na:

`http://.../api/key-value/`