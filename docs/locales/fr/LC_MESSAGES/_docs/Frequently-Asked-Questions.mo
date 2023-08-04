��    &      L              |  -   }  Y   �  0     :   6  W   q  *   �  '   �  -         J  :   k     �     �  6   �  ;     �  K  �    F   �  <   *	  A   g	  !   �	  [   �	    '
  >   <  F   {  �   �  9   M  6  �  �  �  �  n  	  6  �  @  �  .  �    �  �     �  �   �  t  $  �  �!  :   &#  l   a#  /   �#  I   �#  t   H$  3   �$  '   �$  ;   %     U%  H   u%     �%     �%  H   �%  H   F&  *  �&  "  �(  M   �*  N   ++  K   z+     �+  u   �+  u  V,  E   �.  M   /  �   `/  1   0  B  :0  =  }1  �  �5  7  �7  �  �8    �;    �=  
  �@  ;  �B  �    D  �  �D   **1. What technologies is the CMS Built on?** **10. What about NMHS that want to migrate their website? What provision for migration?** **11. What support will be offered by WMO RAF?** **12. How does the CMS work in low internet connectivity** **13. Geo-referenced data visualization: What data sources and formats are supported?** **14. Can they use the CAP editor alone?** **2. Who will manage the CMS Content?** **3. What if an NMHS already has a website?** **4. What does ‘CMS’ mean?** **5. What with NMHSs services that do not have IT people** **6. Security risks?** **7. Where is it hosted?** **8. Is WMO RAF managing or handing over completely?** **9. Training and capacity building: how will it be done?** A fundamental aspect considered during the design and development phase of the CMS was to establish a clear and well-defined system for managing content and page structure. This involved creating a **user-friendly interface with a modern design and intuitive features,** aimed at providing users with a seamless and enjoyable experience. The objective was to enable users to easily locate content and utilize the CMS **without the need for specialized IT skills**. An essential feature provided by the CMS is its capability to **facilitate interactive visualization of georeferenced data**. This includes the ability to upload and visualize gridded data in formats such as NetCDF and GeoTIFF, as well as vector data in the form of points and polygons. The CMS also supports the integration of CAP Alerts and enables the inclusion of data from external Web Map Service (WMS) sources for comprehensive data visualization. Approach and present the CMS to the NMHS. Integrate suggested feedback Assessing Quality and interactivity of existing NMHS website Follow-up support in troubleshooting and resolving technical bugs Frequently Asked Questions (FAQs) Identify departmental focal points for CMS coordination including overall CMS administrator In cases where an NMHS already has an existing website but is interested in testing the new CMS, they have the option to install and run it **concurrently with their existing system** for a specific duration. This allows them to thoroughly evaluate and experience the functionalities offered by the new CMS. Once the NMHS is satisfied and comfortable with the new CMS, a phased approach can be adopted to gradually transition and fully migrate their website to the new CMS. This ensures a smooth and well-managed transition process. Installation and setup of CMS in-premise servers/cloud servers Provision of learning materials, documentations, and guides of the CMS Provision one-on-one training and capacity building to departmental focal points on configuration and customization of the CMS and Website Support on the operationalization of the CMS cuts across: The **NMHS installing the CMS and its components will be fully responsible** for inputting and managing the content that goes into the CMS, from their side. This means that they take the instance of the code and run it, without anyone else having access to the operational instance, unless authorized to do so. The **NMHSs independently manage all components of the CMS in a decentralized manner** at the departmental level. The CMS includes an administrative role (superuser) that possesses complete privileges to access all components of the system. Further information regarding users and roles can be found at (https://github.com/wmo-raf/nmhs-cms/wiki/Manage-Users-and-Roles). It is important to note that WMO RAF does not have involvement in managing the CMS, as its administration and control lie solely with the NMHSs. While WMO RAF does not directly manage the CMS, it does offer valuable support to NMHSs by **providing training and guidance** on the proper management of the CMS. WMO's role is to assist NMHSs in acquiring the necessary knowledge and skills to effectively handle and maintain the CMS. This training and guidance aim to empower NMHSs in utilizing the CMS to its full potential and ensuring optimal performance and functionality. The CAP Editor has been developed to be flexible in its deployment options. It can be run independently as a **standalone application**, which is accessible at https://github.com/wmo-raf/cap-editor. Alternatively, it can be fully **integrated into the CMS**, providing seamless management of CAP Alerts within the CMS environment. More information about the integration and usage can be found at https://github.com/wmo-raf/nmhs-cms/wiki/Manage-CAP-Alerts. The CMS is deployed **at the National Meteorological and Hydrological Service (NMHS) level,** utilising either **cloud-based infrastructure or on-premises servers**. Please refer to the provided **server specifications** for more details on the hosting environment. The CMS is optimized for low bandwidth scenarios. This involves the minimisation of the use of large images, videos or heavy media files that might consume a significant amount of bandwidth. The CMS also supports **caching mechanisms** that can help reduce the load on the server and improve the website’s performance. By enabling caching, static content can be stored on the user's device, reducing the need for repeated downloads, and enhancing the experience on low bandwidth connections. The CMS, along with its various components, is **completely open-source** and developed on the [WMO RAF GitHub account](https://github.com/orgs/wmo-raf). This implies that the institution will have **unrestricted access to the source code**, allowing them to identify and report any bugs, request new features, and even actively contribute to the development of the codebase. This open approach encourages collaboration and fosters a sense of ownership and involvement within the institution. The CMS, which is being built using open-source technologies, benefits from the advantage of having a community of developers who actively contribute to enhancing its security and stability. Furthermore, the CMS offers robust **support for secure authentication mechanisms**, including username/password authentication, integration with third-party authentication systems such as OAuth, and the ability to implement custom authentication backends. Additionally, the CMS performs **regular backups to safeguard the website's data** and enable its restoration in case of data loss. The NMHS are encouraged to share **only the final products** intended for the public. The migration process will commence by initially **identifying the current content of the pages, as well as identifying additional pages that may be relevant and determining any obsolete content**. Moreover, recommendations will be provided regarding optimal practices pertaining to wording, images, colors, and other related aspects. The manual migration of each page will be conducted in collaboration with departmental focal points to ensure efficient coordination. The term ‘CMS’, as used in this document, refers to **all the components** working together to have a running website, more especially on managing the website content. Read more about the CMS Key functionalities https://github.com/wmo-raf/nmhs-cms/wiki This also includes the implementation of CAP Alerts, Georeferenced data visualization, email marketing, events, surveys, and user analytics integration. WMO RAF will conduct training sessions for the CMS, which can be arranged in **either face-to-face or online formats**. Comprehensive **training materials**, including user guides (https://github.com/wmo-raf/nmhs-cms/wiki) and developer guides (https://github.com/wmo-raf/nmhs-cms), are also available. The training sessions will be specifically targeted towards designated **departmental focal points **responsible for each component of the CMS. This approach ensures that the training is tailored to meet the specific needs and roles within the NMHS, enabling efficient knowledge transfer and effective utilization of the CMS. Project-Id-Version: NMHS CMS Documentation 0.5
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2023-08-04 20:05+0900
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language: fr
Language-Team: fr <LL@li.org>
Plural-Forms: nplurals=2; plural=(n > 1);
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Generated-By: Babel 2.12.1
 **1. Sur quelles technologies le CMS est-il construit ?** **dix. Qu'en est-il des SMHN qui souhaitent migrer leur site Web ? Quelle disposition pour la migration ?** **11. Quel soutien sera offert par WMO RAF ?** **12. Comment fonctionne le CMS en cas de faible connectivité Internet** **13. Visualisation des données géoréférencées : quels formats et sources de données sont pris en charge ?** **14. Peuvent-ils utiliser l'éditeur CAP seul ?** **2. Qui gérera le contenu du CMS ?** **3. Que se passe-t-il si un SMHN a déjà un site Web ?** **4. Que signifie « CMS » ?** **5. Qu'en est-il des services des SMHN qui n'ont pas d'informaticiens** **6. Risques de sécurité ?** **7. Où est-il hébergé ?** **8. La RAF de l'OMM gère-t-elle ou transfère-t-elle entièrement ?** **9. Formation et renforcement des capacités : comment cela se fera ?** Un aspect fondamental pris en compte lors de la phase de conception et de développement du CMS était d'établir un système clair et bien défini pour gérer le contenu et la structure des pages. Cela impliquait de créer une **interface conviviale avec un design moderne et des fonctionnalités intuitives**, visant à offrir aux utilisateurs une expérience fluide et agréable. L'objectif était de permettre aux utilisateurs de localiser facilement le contenu et d'utiliser le CMS **sans avoir besoin de compétences informatiques spécialisées**. Une fonctionnalité essentielle fournie par le CMS est sa capacité à **faciliter la visualisation interactive de données géoréférencées**. Cela inclut la possibilité de télécharger et de visualiser des données maillées dans des formats tels que NetCDF et GeoTIFF, ainsi que des données vectorielles sous forme de points et de polygones. Le CMS prend également en charge l'intégration des CAP Alerts et permet l'inclusion de données provenant de sources Web Map Service (WMS) externes pour une visualisation complète des données. Approcher et présenter le CMS au SMHN. Intégrer les commentaires suggérés Évaluation de la qualité et de l'interactivité du site Web existant du SMHN Assistance de suivi dans le dépannage et la résolution de bugs techniques Foire aux questions (FAQ) Identifier les points focaux départementaux pour la coordination du CMS, y compris l'administrateur général du CMS Dans les cas où un SMHN dispose déjà d'un site Web existant mais souhaite tester le nouveau CMS, il a la possibilité de l'installer et de l'exécuter ** en même temps que son système existant ** pendant une durée spécifique. Cela leur permet d'évaluer et d'expérimenter en profondeur les fonctionnalités offertes par le nouveau CMS. Une fois que le SMHN est satisfait et à l'aise avec le nouveau CMS, une approche progressive peut être adoptée pour effectuer progressivement la transition et la migration complète de son site Web vers le nouveau CMS. Cela garantit un processus de transition fluide et bien géré. Installation et configuration de serveurs CMS sur site/serveurs cloud Fourniture de supports d'apprentissage, de documentations et de guides du CMS Offrir une formation individuelle et un renforcement des capacités aux points focaux départementaux sur la configuration et la personnalisation du CMS et du site Web L'appui à l'opérationnalisation du CMS couvre : Le **SMHN installant le CMS et ses composants sera entièrement responsable** de la saisie et de la gestion du contenu qui entre dans le CMS, de son côté. Cela signifie qu'ils prennent l'instance du code et l'exécutent, sans que personne d'autre n'ait accès à l'instance opérationnelle, à moins d'y être autorisé. Les **SMHN gèrent indépendamment tous les composants du CMS de manière décentralisée** au niveau départemental. Le CMS comprend un rôle administratif (superutilisateur) qui possède des privilèges complets pour accéder à tous les composants du système. De plus amples informations concernant les utilisateurs et les rôles sont disponibles sur (https://github.com/wmo-raf/nmhs-cms/wiki/Manage-Users-and-Roles). Il est important de noter que la RAF de l'OMM n'est pas impliquée dans la gestion du CMS, car son administration et son contrôle incombent uniquement aux SMHN. Bien que la RAF de l'OMM ne gère pas directement le CMS, elle offre un soutien précieux aux SMHN en **fournissant une formation et des conseils** sur la bonne gestion du CMS. Le rôle de l'OMM est d'aider les SMHN à acquérir les connaissances et les compétences nécessaires pour gérer et entretenir efficacement le CMS. Cette formation et ces conseils visent à donner aux SMHN les moyens d'utiliser le CMS à son plein potentiel et d'assurer des performances et des fonctionnalités optimales. L'éditeur CAP a été développé pour être flexible dans ses options de déploiement. Il peut être exécuté indépendamment en tant qu'**application autonome**, accessible à l'adresse https://github.com/wmo-raf/cap-editor. Alternativement, il peut être entièrement **intégré dans le CMS**, offrant une gestion transparente des alertes CAP dans l'environnement CMS. Plus d'informations sur l'intégration et l'utilisation sont disponibles sur https://github.com/wmo-raf/nmhs-cms/wiki/Manage-CAP-Alerts. Le CMS est déployé **au niveau du Service météorologique et hydrologique national (SMHN)**, en utilisant soit une **infrastructure basée sur le cloud, soit des serveurs sur site**. Veuillez vous référer aux **spécifications du serveur** fournies pour plus de détails sur l'environnement d'hébergement. Le CMS est optimisé pour les scénarios à faible bande passante. Cela implique la minimisation de l'utilisation d'images volumineuses, de vidéos ou de fichiers multimédias volumineux susceptibles de consommer une quantité importante de bande passante. Le CMS prend également en charge les **mécanismes de mise en cache** qui peuvent aider à réduire la charge sur le serveur et à améliorer les performances du site Web. En activant la mise en cache, le contenu statique peut être stocké sur l'appareil de l'utilisateur, ce qui réduit le besoin de téléchargements répétés et améliore l'expérience sur les connexions à faible bande passante. Le CMS, ainsi que ses différents composants, est **entièrement open-source** et développé sur le [compte GitHub RAF de l'OMM](https://github.com/orgs/wmo-raf). Cela implique que l'institution aura un **accès illimité au code source**, lui permettant d'identifier et de signaler tout bogue, de demander de nouvelles fonctionnalités et même de contribuer activement au développement de la base de code. Cette approche ouverte encourage la collaboration et favorise un sentiment d'appartenance et d'implication au sein de l'institution. Le CMS, qui est construit à l'aide de technologies open source, bénéficie de l'avantage d'avoir une communauté de développeurs qui contribuent activement à améliorer sa sécurité et sa stabilité. En outre, le CMS offre une **prise en charge robuste des mécanismes d'authentification sécurisés**, y compris l'authentification par nom d'utilisateur/mot de passe, l'intégration avec des systèmes d'authentification tiers tels que OAuth et la possibilité de mettre en œuvre des backends d'authentification personnalisés. De plus, le CMS effectue des **sauvegardes régulières pour protéger les données du site Web** et permettre leur restauration en cas de perte de données. Les SMHN sont encouragés à partager **uniquement les produits finaux** destinés au public. Le processus de migration commencera par **identifier initialement le contenu actuel des pages, ainsi que par identifier les pages supplémentaires qui peuvent être pertinentes et déterminer tout contenu obsolète**. De plus, des recommandations seront fournies concernant les pratiques optimales concernant le libellé, les images, les couleurs et d'autres aspects connexes. La migration manuelle de chaque page sera menée en collaboration avec les points focaux départementaux pour assurer une coordination efficace. Le terme « CMS », tel qu'il est utilisé dans ce document, fait référence à **tous les composants** travaillant ensemble pour avoir un site Web opérationnel, plus particulièrement à la gestion du contenu du site Web. En savoir plus sur les fonctionnalités CMS Key https://github.com/wmo-raf/nmhs-cms/wiki Cela inclut également la mise en œuvre des alertes CAP, la visualisation des données géoréférencées, le marketing par e-mail, les événements, les enquêtes et l'intégration de l'analyse des utilisateurs. Le RAF de l'OMM organisera des sessions de formation pour le CMS, qui peuvent être organisées en ** formats en face à face ou en ligne **. **Supports de formation** complets, y compris les guides de l'utilisateur (https://github.com/wmo-raf/nmhs-cms/wiki) et les guides du développeur (https://github.com/wmo-raf/nmhs-cms) , sont également disponibles. Les sessions de formation seront spécifiquement destinées aux **points focaux départementaux** responsables de chaque composante du CMS. Cette approche garantit que la formation est adaptée pour répondre aux besoins et aux rôles spécifiques au sein du SMHN, permettant un transfert efficace des connaissances et une utilisation efficace du CMS. 