# Humane Intel TDX Remote Attestation Framework for baremetal environment (Humane-RAFW-TDX)
(日本語での説明は後半にあります/Japanese version is below)

This repository stores the code and resources for an RA framework (RAFW) that makes it easy to perform Intel TDX's DCAP-based Remote Attestation (RA) in its complete, officially-intended form — with verification collateral (collateral) cached on a PCCS caching server — at a "humane" level of difficulty.

However, this repository assumes a scenario in which a TDX environment is built on a bare-metal machine, a TD is run on top of it, and RA is performed against that TD. In particular, please note that it is fundamentally incompatible with attestation on TDX VM instances in Azure.

* Compared with Intel SGX, which shares the same RA infrastructure, the [official TDX RA sample](https://github.com/intel/confidential-computing.tee.dcap/blob/DCAP_1.25/QuoteGeneration/quote_wrapper/tdx_attest/test_tdx_attest.c) has been dramatically improved. However, the verifier-side sample code is provided as a separate program and is not an end-to-end form. This repository provides a convenient interface that lets you complete RA simply by calling a single function, dramatically improving the difficulty of E2E RA implementation.

* As with its predecessor [Humane-RAFW](https://github.com/acompany-develop/Humane-RAFW) — the EPID-RA framework in the Humane-AFW series — this repository eliminates the complex, hard-to-understand auto-generation elements based on Automake and shell scripts, so developers can concisely add any new elements they want to the Makefile or code.

* This repository uniquely establishes and describes in detail the procedures — including TDX host-side configuration, how to build a TD, in-TD configuration, and PCCS construction — that are highly scattered across versions and references. You are therefore less likely to fall into the situation where you have something to run on TDX, but don't even know how to build TDX on bare metal in the first place.

* Unlike SGX, TDX is a CVM and therefore offers very high flexibility in the workloads you can run, so the contents of this repository are basically implemented in Python. The verifier-side code uses QvL (shared with SGX), and this too can be operated from Python via FFI. In any case, you will not be bothered by communication functions with fatal overhead like msgio from the old EPID-RA official sample.

* This repository adopts Attested-TLS as the cryptographic communication method between the Relying Party (RP) and the Attester. Specifically, by adopting certificate pinning without hostname verification, and by having the RP and the Attester perform a TLS handshake to establish a cryptographic communication channel while applying MITM countermeasures and freshness countermeasures via Report Data, we can guarantee that the communication peer is genuinely an RA-verified workload inside a TEE. Such an implementation does not exist in the official DCAP-RA sample, so this greatly reduces the effort required to implement the cryptographic communication channel.

* By configuring the contents of a TOML file (`reference.toml`), the RP can finely specify the expected measurements (reference measurements) and other conditions for acceptance. This allows the conditions for accepting an Attester to be set at high granularity.

* By displaying the contents of the Quote and Supplemental Data with labels, the actual state of the TD under verification becomes easier to grasp. In addition, TD Quote supports both version 4 (`sgx_quote_4.h` compliant) and version 5 (`sgx_quote_5.h`).

* The Verifier function is designed to be served by the RP side. This eliminates the need to trust a third-party verification agency, making the trust boundary smaller.

* QvL is used for verification; QvE is not used. This is because adopting QvE would require the Verifier (RP) to also prepare an SGX-capable machine. Furthermore, since it is impossible to perform LA on an SGX Enclave from a TD, it cannot be used as a high-trust local Verifier in mutual RA either. Thus, there is almost no benefit to using QvE in TDX, so we deliberately do not adopt it.

* By binarizing the code with PyInstaller and executing it, it becomes measurable by IMA's execution-time check. This makes IMA measurement possible without having to enable file-read-time checks, which tend to bloat the logs.

## Verified Environment
### Attester
* Host OS: Ubuntu 25.10
* Host OS kernel: 6.17.0-20-generic
* TDX Module version: 1.5.13 (identified from the MRSEAM value)
* Guest OS: Ubuntu 24.04.4 LTS
* Guest OS kernel: 6.8.0-107-generic
* SGX DCAP: version 1.25

### Relying Party
* OS: Ubuntu 24.04.4 LTS
* OS kernel: 6.17.0-1010-azure
* SGX DCAP: version 1.25

## TDX Environment Setup
Although this is not directly related to RA, building TDX on a bare-metal machine is notoriously cumbersome. This README therefore also describes a minimal environment setup procedure — without enabling features such as full-disk encryption — to get to the point where a TD can be launched and RA can be performed. If you do not need this, please skip ahead to the next section.

### Memory Requirements
This is an easy blind spot, but TDX depends on SGX in order to perform RA. SGX has a specification where it cannot be enabled unless at least one DIMM (main memory) is inserted in every memory channel. Therefore, consult the manual for your machine and the actual memory layout of that machine, and verify that DIMMs are inserted in every memory channel (you do not need to fill every memory slot).

### BIOS Settings
BIOS settings vary widely across motherboard vendors, so there are parts that cannot be described uniformly.
For example, on a DELL PowerEdge R660 machine, TDX can be enabled with settings such as the following:
* Enter the BIOS settings screen with F2.
* Enter System BIOS.
* From Processor Settings, make the following changes:
    * Set CPU Physical Address Limit to Disabled.
    * Set Sub NUMA Cluster to 2-Way Clustering.
    * From a TEE security perspective, we recommend keeping Logical Processor Disabled.
* From System Security, make the following changes:
    * Set Memory Encryption to Multiple Keys.
    * Set Intel TDX to Enabled.
    * Set TDX SEAM to Enabled.
    * Set Intel SGX to Enabled.
* Confirm the following in Memory Settings:
    * Confirm that Node Interleaving is Disabled. Somewhat confusingly, when this is Disabled, NUMA is actually enabled.

Settings such as Sub NUMA are not specified in Dell's procedure, but they are described in Supermicro's procedure, so we list them here just in case. On Supermicro, there is also a setting for how many bits the HKID — which functions as an identifier for the memory encryption key in the physical address range — should be (TME-MT Key ID Bits or TME-MT/TDX Key Split).

Since we cannot fully explain each of these, please refer to each vendor's manual. As examples, links to Intel's official, Dell's, and Supermicro's documents are shown below:
- Intel: https://cc-enabling.trustedservices.intel.com/intel-tdx-enabling-guide/04/hardware_setup/
- Dell: https://www.dell.com/support/kbdoc/en-us/000226452/enableinteltdxondell16g
- Supermicro (for the X13DEG-R motherboard): https://www.supermicro.com/manuals/motherboard/X13/MNL-2645.pdf

### Host OS Setup
Perform this procedure on the host OS of the Attester side.
- First, running the following command will likely produce output similar to the below, which needs to be corrected.
    ```sh
    acompany@phy:~$ sudo dmesg | grep -i tdx
    [sudo: authenticate] Password: 
    [    8.185161] virt/tdx: BIOS enabled: private KeyID range [32, 64)
    [    8.185165] virt/tdx: initialization failed: Hibernation support is enabled
    ```

* Open `/etc/default/grub` and modify it as follows:
    ```sh
    # Before
    GRUB_CMDLINE_LINUX=""

    # After
    GRUB_CMDLINE_LINUX="nohibernate kvm_intel.tdx=1"
    ```

* Apply the change and reboot:
    ```sh
    sudo update-grub
    sudo reboot
    ```

* After reboot, run the same command as before. If the output looks like below, it succeeded.
    ```sh
    acompany@phy:~$ sudo dmesg | grep -i tdx
    [    0.000000] Command line: BOOT_IMAGE=/vmlinuz-6.17.0-20-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro nohibernate kvm_intel.tdx=1 crashkernel=2G-4G:320M,4G-32G:512M,32G-64G:1024M,64G-128G:2048M,128G-:4096M
    [    4.653640] Kernel command line: BOOT_IMAGE=/vmlinuz-6.17.0-20-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro nohibernate kvm_intel.tdx=1 crashkernel=2G-4G:320M,4G-32G:512M,32G-64G:1024M,64G-128G:2048M,128G-:4096M
    [    8.676579] virt/tdx: BIOS enabled: private KeyID range [32, 64)
    [    8.676583] virt/tdx: Disable ACPI S3. Turn off TDX in the BIOS to use ACPI S3.
    [   38.215820] virt/tdx: 6303780 KB allocated for PAMT
    [   38.215825] virt/tdx: module initialized
    ```

* Run the following commands to install QEMU and libvirt:
    ```sh
    sudo apt update
    sudo apt install qemu-system-x86 libvirt-daemon-system libvirt-clients
    ```

* Add the executing user to the kvm group:
    ```sh
    sudo usermod -aG kvm $USER
    ```

* Once the group addition has taken effect (e.g., after a reboot), open `/etc/libvirt/qemu.conf` with root privileges (with sudo) and append the following three lines to the end of the file:
    ```sh
    user = "<your_user_name>"
    group = "kvm"
    dynamic_ownership = 0
    ```
    The `<your_user_name>` part should be the currently running user's name (e.g., `user = "acompany"`).

* Restart `libvirtd`, then reboot the machine:
    ```sh
    sudo systemctl restart libvirtd
    sudo reboot
    ```
    After reboot, confirm that libvirtd is active.

### Creating and Starting the TD Image
Perform this on the host of the Attester machine.
* Clone Canonical's TDX repository.
    ```sh
    git clone https://github.com/canonical/tdx.git
    ```

* Create a TD image based on Ubuntu 24.04. As of 2026/4/16, creation on Ubuntu 25.04 is also possible. However, it has not yet been verified whether creation works on Ubuntu 25.10, where various CVM features including TDX have been in-kernelized.
    ```sh
    cd tdx/guest-tools/image/
    sudo ./create-td-image.sh -v 24.04
    ```
    When the TD image is created successfully, a message similar to the following will appear near the end:
    ```sh
    SUCCESS: Run setup scripts inside the guest image
    INFO: Cleanup!
    SUCCESS: TDX guest image : /home/acompany/Develop/tdx-ncc/tdx/guest-tools/image/tdx-guest-ubuntu-24.04-generic.qcow2
    ```

* To receive communication from the Relying Party (RP), you need to set up connectivity to the TD. There are many ways to do this; this time we use a very simple configuration where a local IP is assigned to the TD and external communication on the necessary ports is routed to the TD. In a production environment or real deployment, it is better to, for example, create a bridge. First, identify the network interface currently in use.
    ```sh
    ip route show
    ```
    The output will look like below; note down the network interface name on the first line. In the example below, `ens51f0np0` is the relevant one.
    ```sh
    default via 133.125.0.1 dev ens51f0np0 proto static 
    133.125.0.0/24 dev ens51f0np0 proto kernel scope link src 133.125.0.65 
    192.168.122.0/24 dev virbr0 proto kernel scope link src 192.168.122.1
    ```
    You just need to identify the interface that has the machine's IP assigned to it, so of course using other methods such as `ifconfig` is also fine. You will use the identified interface name later, so be sure to note it down.

* Open `guest-tools/trust_domain.xml.template` inside the Canonical TDX repository folder (`tdx`) you cloned earlier, and delete the following portion:
    ```xml
    <qemu:commandline>
        <qemu:arg value='-device'/>
        <qemu:arg value='virtio-net-pci,netdev=nic0,bus=pcie.0,addr=0x5'/>
        <qemu:arg value='-netdev'/>
        <qemu:arg value='user,id=nic0,hostfwd=tcp::0-:22'/>
    </qemu:commandline>
    ```
    You may want to back up this xml.template file in advance as a precaution.

* Still inside the `guest-tools` folder, run the following command to create the TD:
    ```sh
    ./tdvirsh new --td-image ./image/tdx-guest-ubuntu-24.04-generic.qcow2
    ```

* Execution will complete after a few minutes. Use the following command to verify that it was created successfully. At this time, an IP address will be displayed as shown, so be sure to note this IP address down.
    ```sh
    acompany@phy:~/Develop/tdx-ncc/tdx/guest-tools$ ./tdvirsh list
    Id   Name                                                        State 
    ---------------------------------------------------------------------------- 
    8    tdvirsh-trust_domain-84fcc6bb-ca37-400c-9a39-57ec5a92c0b3   running (ip:192.168.122.30, hostfwd:, cid:3)
    ```

* As an aside, you can also log into the TD via console. The username is `tdx`, and the password is `123456`.
    ```sh
    ./tdvirsh console tdvirsh-trust_domain-e98650e2-8ab1-4663-9831-1913e224af64
    login: tdx
    password: 123456
    ```
    After that, on Mac you can exit the console with Command+].

* On the host side, apply the following iptables configuration. The example below assumes the IP address inside the TD is 192.168.122.30.
    ```sh
    sudo iptables -t nat -A PREROUTING -p tcp --dport 8443 -j DNAT --to-destination 192.168.122.30:8443

    sudo iptables -I FORWARD 1 -i ens51f0np0 -o virbr0 -p tcp --dport 8443 -d 192.168.122.30 -j ACCEPT
    sudo iptables -I FORWARD 2 -i virbr0 -o ens51f0np0 -m state --state RELATED,ESTABLISHED -j ACCEPT

    sudo iptables -t nat -A PREROUTING -p tcp --dport 2222 -j DNAT --to-destination 192.168.122.30:22
    sudo iptables -I FORWARD 3 -i ens51f0np0 -o virbr0 -p tcp --dport 22 -d 192.168.122.30 -j ACCEPT
    ```
    In reality, the IP and network interface will be different, so replace the `192.168.122.30` part and the `ens51f0np0` part with the actual values of your environment.  
    If you reboot the TD, the IP may change, so re-run the iptables procedure after running the following commands:
    ```sh
    sudo iptables -t nat -F PREROUTING
    sudo iptables -D FORWARD 1
    sudo iptables -D FORWARD 1
    ```

* Log into the TD via SSH.
    ```sh
    ssh -p 22 root@<the IP above> # privileged user
    ssh -p 22 tdx@<the IP above> # unprivileged user
    ```

* While you are logged in, go ahead and finish the basic settings inside the TD. First, to configure the communication method with QGS (the TD Quote generation service), run the following command inside the TD:
    ```sh
    sudo tee -a /etc/tdx-attest.conf > /dev/null <<EOT
    port=4050
    EOT
    ```

* Next, run the following commands inside the TD to add the GPG key for the Intel TDX/SGX repository:
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* Inside the TD, open `/etc/apt/sources.list.d/ubuntu.sources` with root privileges and append the following at the end:
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```
    Then run apt update:
    ```sh
    sudo apt update
    ```

* Install the TDX RA library inside the TD.
    ```sh
    sudo apt install -y libtdx-attest libtdx-attest-dev
    ```

### IMA Setup Inside the TD
To measure content beyond the OS kernel — such as user workloads — you must use Linux's IMA feature. So we configure IMA as well.
* Log into the TD and create a folder called `ima` under `/etc/`.
    ```sh
    sudo mkdir /etc/ima
    ```

* Move into the folder you created and create a file called `ima-policy`. **From this point on, if the TD is powered off in an incomplete state, it may lead to unrecoverable destruction, so do not shut down the TD by any method other than the procedure that follows.**
    ```sh
    cd /etc/ima
    sudo touch ima-policy
    ```

* Write the following content into the file you just created. The FILE_CHECK line can remain commented out if it is not needed.
    ```
    # PROC_SUPER_MAGIC
    dont_measure fsmagic=0x9fa0
    # SYSFS_MAGIC
    dont_measure fsmagic=0x62656572
    # DEBUGFS_MAGIC
    dont_measure fsmagic=0x64626720
    # TMPFS_MAGIC
    dont_measure fsmagic=0x1021994
    # DEVPTS_SUPER_MAGIC
    dont_measure fsmagic=0x1cd1
    # BINFMTFS_MAGIC
    dont_measure fsmagic=0x42494e4d
    # SECURITYFS_MAGIC
    dont_measure fsmagic=0x73636673
    # SELINUX_MAGIC
    dont_measure fsmagic=0xf97cff8c
    # SMACK_MAGIC
    dont_measure fsmagic=0x43415d53
    # CGROUP_SUPER_MAGIC
    dont_measure fsmagic=0x27e0eb
    # CGROUP2_SUPER_MAGIC
    dont_measure fsmagic=0x63677270
    # NSFS_MAGIC
    dont_measure fsmagic=0x6e736673 

    # Configuration of measurement targets and triggers

    # Measure files MMAP'd when programs are executed
    measure func=MMAP_CHECK mask=MAY_EXEC

    # Measure executed binary programs
    measure func=BPRM_CHECK mask=MAY_EXEC

    # Measure files opened by root (uid=0)
    # measure func=FILE_CHECK mask=MAY_READ uid=0

    # Measure loaded kernel modules
    measure func=MODULE_CHECK

    # Measure firmware loaded into the kernel
    measure func=FIRMWARE_CHECK
    ```

* Log out from the TD and return to the host OS.

* Move to the `guest-tools` folder inside the Canonical tdx repository folder mentioned earlier, where tdvirsh is located. As needed, check the TD's Name with `./tdvirsh list --all`.

* Shut down the TD with the following command:
    ```sh
    ./tdvirsh shutdown <tdname>
    ```
    Example:
    ```sh
    ./tdvirsh shutdown tdvirsh-trust_domain-745eb08d-790c-4685-81c4-92ae69119a68
    ```

* Confirm that the TD has been shut down.
    ```sh
    ./tdvirsh list --all
    Id   Name                                                        State 
    ---------------------------------------------------------------------------- 
    -    tdvirsh-trust_domain-745eb08d-790c-4685-81c4-92ae69119a68   shut off (ip:unknown, hostfwd:, cid:)
    ```

* Start the TD you just shut down. This counts as a reboot, and the IMA policy you added will take effect.
    ```sh
    ./tdvirsh start <tdname>
    ```

### Building the TDX RA Infrastructure
The simplest option would be to keep everything self-contained on the TDX machine, but for extensibility we describe a setup in which the Verifier and RP are placed on a separate machine.

In our setup, we stand up a suitable instance in Azure (e.g., Standard D4s v5), but you are not required to do so. We use Ubuntu 24.04 as the OS. Below, we refer to this machine as the "RP machine".

#### Building the PCCS
Perform this on the RP machine.
* Run the following commands to add Intel's GPG key.
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* Open `/etc/apt/sources.list.d/ubuntu.sources` and add the following at the bottom:
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* Apply the above addition.
    ```sh
    sudo apt update
    ```

* Install the prerequisite packages required by PCCS.
    ```sh
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -yq --no-install-recommends nodejs=20.11.1-1nodesource1
    sudo apt-get install -y cracklib-runtime
    ```

* Install PCCS.
    ```sh
    sudo apt install -y --no-install-recommends sgx-dcap-pccs
    ```
    You will be prompted interactively as follows; enter the values as shown below. In particular, be sure to set Caching Fill Method to LAZY.
    ```
    Do you want to install PCCS now? (Y/N) :y
    Enter your http proxy server address, e.g. http://proxy-server:port (Press ENTER if there is no proxy server) :
    Enter your https proxy server address, e.g. http://proxy-server:port (Press ENTER if there is no proxy server) :

    Do you want to configure PCCS now? (Y/N) :y
    Set HTTPS listening port [8081] (1024-65535) :
    Set the PCCS service to accept local connections only? [Y] (Y/N) :n
    Set your Intel PCS API key (Press ENTER to skip) :<PCS_PRIMARY_KEY>
    Choose caching fill method : [LAZY] (LAZY/OFFLINE/REQ) :LAZY

    Set PCCS server administrator password:<any PCCS administrator password>
    Re-enter administrator password:<re-enter the PCCS administrator password>
    Set PCCS server user password:<any PCCS user password>
    Re-enter user password:<re-enter the PCCS user password>

    Do you want to generate insecure HTTPS key and cert for PCCS service? [Y] (Y/N) :y
    Certificate request self-signature ok
    subject=CN = PCCS Server (self-signed certificate)
    Installing PCCS service ...Created symlink /etc/systemd/system/multi-user.target.wants/pccs.service → /usr/lib/systemd/system/pccs.service.
    finished.
    Installation completed successfully.
    ```
    You obtain the PCS API key from the following link (proceed via the Subscribe button on the linked page):  
    https://api.portal.trustedservices.intel.com/provisioning-certification  
    Also, be sure to keep the PCCS administrator/user passwords where you will not lose them.

#### Preparing PCCS Collateral (Attester)
Return temporarily to the TDX machine (Attester machine) and prepare the collateral — the attached information required for RA. This assumes that the TDX machine is a multi-CPU machine, but the same procedure should work for a single-CPU machine as well (requires verification).
* On the host side of the TDX machine, run the following commands to add Intel's GPG key:
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* Open `/etc/apt/sources.list.d/ubuntu.sources` and add the following at the bottom:
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```
    Since Intel has not yet prepared a repository for 25.10, we substitute the one for 24.04 (noble).

* Apply the above addition.
    ```sh
    sudo apt update
    ```

* Install PCKCIDRT (PCK Cert ID Retrieval Tool).
    ```sh
    sudo apt install -y sgx-pck-id-retrieval-tool
    ```

* Run PCKCIDRT to obtain a CSV containing the Platform Manifest, etc.
    ```sh
    cd /opt/intel/sgx-pck-id-retrieval-tool
    sudo ./PCKIDRetrievalTool -f host_$(hostnamectl --static).csv
    ```
    **Once obtained, this CSV cannot be retrieved again until an SGX Factory Reset is performed, so be careful not to lose it.**

* Extract the Platform Manifest from the above CSV in binary form.
    ```sh
    sudo apt-get install -y csvtool
    sudo bash -c "csvtool col 6 host_$(hostnamectl --static).csv | xxd -r -p > host_$(hostnamectl --static)_pm.bin"
    ```

* Send the Platform Manifest binary to IRS (Intel Registration Service).
    ```sh
    curl -i \
        --data-binary @host_$(hostnamectl --static)_pm.bin \
        -X POST "https://api.trustedservices.intel.com/sgx/registration/v1/platform" \
        -H "Content-Type: application/octet-stream"
    ```
    On success, you should see an HTTP success status like the following:
    ```
    HTTP/1.1 201 Created
    Content-Length: 32
    Content-Type: text/plain
    Request-ID: adcc371c43d84b12bbd6fd334651fdfc
    Date: Mon, 06 Apr 2026 05:53:15 GMT
    ```

* Return to your working folder temporarily and clone the DCAP library.
    ```sh
    git clone --recursive https://github.com/intel/confidential-computing.tee.dcap.git
    ```

* Install the required packages.
    ```sh
    sudo apt install -y python3 python3-pip python3-venv
    ```

* Move to the PCS Client Tool folder and activate the venv. Then install the required Python packages.
    ```sh
    cd confidential-computing.tee.dcap/tools/PcsClientTool/
    python3 -m venv venv
    source ./venv/bin/activate
    pip install -r requirements.txt
    ```

* Copy the CSV obtained earlier with PCKCIDRT into the PCS Client Tool folder.
    ```sh
    cp /opt/intel/sgx-pck-id-retrieval-tool/host_$(hostnamectl --static).csv .
    ```

* Run the following command to collect platform information:
    ```sh
    python3 ./pcsclient.py collect -d .
    ```

* Run the following command to collect the collateral, and then exit the venv environment.
    ```sh
    ./pcsclient.py fetch -t early -o platform_collaterals.json
    deactivate
    ```
    If you are following this repository's procedure on GCP or similar, it is better to run the following command instead for collection. Even on bare metal, running the following command is unlikely to cause problems.
    ```sh
    ./pcsclient.py fetch -p all -t early -o platform_collaterals.json
    ```
    In either case, you will be asked for the PCS API key along the way, so enter the key you noted down in the earlier procedure. Immediately afterwards, you will be asked whether to register it with the Keyring; decline (enter n).  
    Also, you may see output like the following, which you can ignore by responding as shown:
    ```
    Some certificates are 'Not available'. Do you want to save the list?(y/n)y
    Please input file name (Press enter to use default name not_available.json):
    Please check not_available.json for 'Not available' certificates.
    ```

#### Preparing PCCS Collateral (RP)
Perform the procedure in this section on the RP machine.
* Clone the repository that contains PCCS Admin Tool.
    ```sh
    git clone --recursive https://github.com/intel/confidential-computing.tee.dcap.pccs.git
    ```

* Move into the PccsAdminTool folder inside the cloned folder and create a venv environment.
    ```sh
    cd confidential-computing.tee.dcap.pccs/PccsAdminTool
    sudo apt install python3-venv
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

* Bring the `platform_collaterals.json` obtained earlier on the Attester machine over to the RP machine using scp, a USB drive, etc.

* Register the collected collateral with the PCCS on the RP machine.
    ```sh
    ./pccsadmin.py put -i platform_collaterals.json
    deactivate
    ```

* Access to the PCCS on the RP machine will occur over port 8081 during RA. Therefore, if your RP machine is an Azure VM or similar, configure an inbound port rule from the VM management page to allow traffic to port 8081. If the RP runs on a bare-metal machine, likewise check that a firewall or similar is not blocking it.

#### Setting Up the TD Quote Generation Environment
Perform this on the Attester (TDX) machine.
* On the host side, run the following command to install QGS (Quote Generation Service) and its required packages.
    ```sh
    sudo apt install -y \
    tdx-qgs \
    libsgx-dcap-default-qpl \
    libsgx-dcap-ql
    ```

* If you want to inspect the service logs for QGS, optionally run the following command:
    ```sh
    sudo journalctl -u qgsd -f
    ```
    If output like the following appears, it is working normally:
    ```
    Apr 06 06:15:35 phy usermod[94009]: add 'qgsd' to group 'sgx_prv'
    Apr 06 06:15:35 phy usermod[94009]: add 'qgsd' to shadow group 'sgx_prv'
    Apr 06 06:15:35 phy usermod[94016]: add 'qgsd' to group 'sgx'
    Apr 06 06:15:35 phy usermod[94016]: add 'qgsd' to shadow group 'sgx'
    Apr 06 06:15:35 phy qgs[94024]: Parameters from configuration file: num_thread = 4, port = 4050 (0fd2h)
    Apr 06 06:15:35 phy qgs[94024]: Parameters after command line check: num_thread = 4, port = 4050 (0fd2h)
    Apr 06 06:15:35 phy systemd[1]: Started qgsd.service - Intel(R) TD Quoting Generation Service.
    Apr 06 06:15:35 phy qgsd[94027]: Added signal handler
    Apr 06 06:15:35 phy qgsd[94027]: About to create QgsServer
    Apr 06 06:15:35 phy qgsd[94027]: About to start main loop
    ```

* Configure `/etc/sgx_default_qcnl.conf` to specify the destination for collateral retrieval, etc.
    ```sh
    sudo vim /etc/sgx_default_qcnl.conf
    ```
    The following part is `true` by default; change it to `false`.
    ```json
    ,"use_secure_cert": false
    ```
    If PCCS uses a proper, non-self-signed certificate, this should actually be set to true; however, since this concerns a server certificate that is not directly related to TEE RA, we simplify here using a self-signed certificate.  
    Also, change the `localhost` portion of `"pccs_url"` to the actual IP address of the RP/Verifier machine.

* Restart the service so that the above changes take effect.
    ```sh
    sudo systemctl restart qgsd.service
    ```

### Running the TDX Attestation Sample
* Log into the TD and run the following commands:
    ```sh
    cd /opt/intel/tdx-quote-generation-sample/
    sudo make
    sudo ./test_tdx_attest
    ```
    If it succeeds, creation of a TD Quote will succeed. The fact that Extend to RTMR2/3 does not work is a bug already present in the Linux kernel version that Ubuntu 24.04 uses by default. Upgrading the kernel to 6.16 or later enables Extend, but we omit that procedure here.

## Preparing and Running the RA Framework
This section describes the procedure for actually performing TDX RA using the framework this repository provides.

### Attester-Side Preparation
* Clone this repository inside the TD.
    ```sh
    git clone https://github.com/acompany-develop/Humane-RAFW-TDX.git
    ```

* Enter the `attester` folder inside the repository folder.
    ```sh
    cd attester
    ```

* Run the following commands to set up the venv environment.
    ```sh
    sudo apt install python3-venv
    python3 -m venv venv 
    source venv/bin/activate
    ```

* Install the required Python packages.
    ```sh
    pip3 install -r requirements.txt
    ```

### RP-Side Preparation
* Run the following command to install the required packages.
    ```sh
    sudo apt install -y libsgx-dcap-quote-verify-dev libsgx-dcap-default-qpl libsgx-dcap-default-qpl-dev libsgx-enclave-common-dev libtdx-attest libtdx-attest-dev
    ```

* Configure `/etc/sgx_default_qcnl.conf` to specify the destination for collateral retrieval, etc. Since collateral is also used when verifying Quotes, configuration is required on the RP side as well.
    ```sh
    sudo vim /etc/sgx_default_qcnl.conf
    ```
    The following part is `true` by default; change it to `false`.

* Restart the PCCS service so that the changes take effect.
    ```sh
    sudo systemctl restart pccs.service
    ```

* Clone this repository.
    ```sh
    git clone https://github.com/acompany-develop/Humane-RAFW-TDX.git
    ```

* Run the following commands to set up the venv environment.
    ```sh
    sudo apt install python3-venv
    python3 -m venv venv 
    source venv/bin/activate
    ```

* Install the required Python packages.
    ```sh
    pip3 install -r requirements.txt
    ```

### Obtaining Reference Measurements
In operations, this procedure is expected to be performed by an RP operator who logs into the Attester machine. It assumes a scenario in which the RP obtains reference measurements in advance, before deploying the Attester machine remotely.
* Complete all the configuration described above inside the TD of the Attester machine.

* If you have completed the procedure, you should already be inside the `attester`-side venv. Staying in that state, move to the `relying-party/reference-tool` folder inside this repository's folder in the TD of the Attester machine.

* Run the following command to execute the reference measurement retrieval tool:
    ```sh
    sudo make all
    ```
    Note that without sudo, the Quote cannot be obtained, and execution fails.  
    If execution succeeds, output like the following appears:
    ```
    [*] Generating TD Quote...
    [*] Quote size: 5243 bytes
    [*] Quote version : 4
    [*] TEE type      : 0x00000081

    === Reference Measurements ===
    MRSEAM         : 27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec

    MRSIGNERSEAM   : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MRTD           : eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542

    MRCONFIGID     : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MROWNER        : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MROWNERCONFIG  : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    RTMR[0]        : 2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d

    RTMR[1]        : f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877

    RTMR[2]        : 4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b

    RTMR[3]        : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
    ```
    Copy this content and keep it aside.

* Go back to the RP machine and copy `reference_template.toml` in the `relying-party` folder to `reference.toml`.
    ```sh
    cp reference_template.toml reference.toml
    ```

* Open reference.toml. On the right-hand side of `mr_seam`, `mrsigner_seam`, `mr_td`, `mrconfigid`, `mrowner`, `mrownerconfig`, and `rtmr0`-`rtmr3`, paste the hex strings displayed by the reference measurement retrieval tool, surrounded by double quotes.  
    Example:
    ```toml
    [measurements]
    mr_seam = "27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec"
    mrsigner_seam = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_td = "eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542"

    mr_config_id = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_owner = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_owner_config = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

    rtmr0 = "2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d"
    rtmr1 = "f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877"
    rtmr2 = "4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b"
    rtmr3 = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    ```

* The remaining fields in the toml can be left at their default values if not needed. If needed, change them appropriately using the following as a reference.
    | Field Name | Description | Recommended Value |
    |---|---|---|
    | `allow_debug` | Whether to allow the TD's debug mode. When debug mode is enabled, the memory contents of the TD can be read and written from outside in plaintext through a dedicated interface, so it must not be used in production. | `false` |
    | `allow_collateral_expiration` | Whether to allow expiration of the attached information (collateral) used for RA. Since expiration does not immediately pose a risk, it can be tolerated for the time being. For reference, in Azure, management lags, so RA must be performed with expired collateral unconditionally. | `true` |
    | `allow_configuration_needed` | Whether to permit `CONFIGURATION_NEEDED`, one of the RA statuses. It means the TEE is up to date, but some machine configuration change is required to improve safety. In the older EPID-RA for SGX, this status appeared, for example, when hyper-threading was enabled; in the current SGX/TDX DCAP-RA it does not appear even when hyper-threading is enabled, so what actually triggers it is unclear. If you cannot get rid of this status, you can accept it while acknowledging a certain level of risk. | `false` |
    | `allow_sw_hardening_needed` | Whether to permit `SW_HARDENING_NEEDED`, one of the RA statuses. It means the machine and TDX components are up to date, but in order to neutralize vulnerabilities, the contents inside the TD (user workloads, etc.) also need to apply software-level countermeasures on their own. If the status cannot be resolved even with TCB Recovery (Attester machine BIOS update, etc.), you can accept it while acknowledging a certain level of risk. | `false` |
    | `allow_out_of_date` | Whether to permit `OUT_OF_DATE`, one of the RA statuses. It means the machine or installed TDX is outdated and a certain level of safety cannot be maintained. It can sometimes be resolved via TCB Recovery, but for the given machine (CPU) Intel may have discontinued updates, or even when Intel distributes an update, the motherboard vendor may not have made it installable, so when this appears, mitigation tends to be difficult. In principle, we strongly recommend rejecting it. | `false` |
    | `allow_td_relaunch_advised` | Whether to permit `TD_RELAUNCH_ADVISED`, one of the RA statuses. It means the TDX-related components on the machine side are up to date, but since the target TD was launched before they were brought up to date, restarting the TD is recommended. We have not confirmed a concrete real-world case, but it is believed to be fixed by a restart. It is also best to reject this RA status. | `false` |
    | `allow_smt_enabled` | Whether to allow hyper-threading to be enabled. Since hyper-threading potentially facilitates attacks against the TEE (e.g., ZombieLoad, Gather Data Sampling), it is preferable to disable it. | `false` |
    | `required_tcb_eval_ds_num` | Specifies the minimum acceptable value of the TCB Evaluation Dataset Number, a value that concisely expresses the security version of the TDX environment in question. If not needed, 0 is fine. | Determine the setting from the number to the right of `TCB-R Counter:` in the table on [this](https://www.intel.com/content/www/us/en/developer/topic-technology/software-security-guidance/trusted-computing-base-recovery-attestation.html) page and the contents of the table. 0 if not needed. |
    | `allowed_sa_list` | List of allowed vulnerabilities. For Intel-related vulnerabilities, Intel publishes Security Advisories (SA), each with its own ID. For example, SGX's MMIO Stale Data vulnerability is assigned the ID `INTEL-SA-00615`. In this field, specify, by SA ID, the vulnerabilities that you have decided to allow after considering the risks. If you do not want to allow any, leave it empty. | empty |

### Running the Attester Side
* With the `attester`-side venv active, run the following command inside the `attester` folder of this repository within the TD:
    ```sh
    sudo make all
    ```
    Note: without sudo, the Quote cannot be obtained, resulting in an error.

### Running the RP Side
* With the `relying-party`-side venv active, run the following command inside the `relying-party` folder of this repository on the RP machine:
    ```sh
    make all
    ```

### Example Runs
#### Attester
```
INFO:     Started server process [13607]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8443 (Press CTRL+C to quit)
INFO:     20.243.195.59:60112 - "POST /attest HTTP/1.1" 200 OK
INFO:     20.243.195.59:60118 - "POST /add HTTP/1.1" 200 OK
```

#### RP
```
(venv) user@machine:~/Develop/tdx/Humane-RAFW-TDX/relying-party$ sudo make
./venv/bin/python3 rp_client.py
[config] ATTESTER_URL = https://133.125.0.65:8443/
/home/aos/Develop/tdx/Humane-RAFW-TDX/relying-party/venv/lib/python3.12/site-packages/urllib3/connectionpool.py:1097: InsecureRequestWarning: Unverified HTTPS request is being made to host '133.125.0.65'. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
  warnings.warn(
Obtained TD Quote successfully.
Quote size: 5243 bytes
Nonce sent: 86c33b6891453d35e012ee74e6237a31d5ff77e2b041026b5da58e01e502cc30
Saved pinned certificate: ./pinned_attester_cert.pem
Saved TD Event Log: ./tdeventlog.txt
Saved IMA runtime measurements: ./ima_runtime_measurements.txt

Quote version -> 4

TEE type -> 0x81


[Report Body in TD Quote]
MRSEAM               -> 27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec

MRSIGNERSEAM         -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

SEAM Attributes      -> 0000000000000000

TD Attributes        -> 0000001000000000

XFAM                 -> e702060000000000

MRTD                 -> eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542

MRCONFIGID           -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

MROWNER              -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

MROWNERCONFIG        -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

RTMR[0]              -> 2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d

RTMR[1]              -> f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877

RTMR[2]              -> 4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b

RTMR[3]              -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

Report Data          -> 3d78d26597dadc7f0190f2a878129aedbb24b3e5a8c370c5a9f291c1faf3440dfc99e98510bd89382a1d5856fe47bcfd0f3d102ec48f92f474cf01757e0d05e4

Is TD in Debug mode? -> False

Collateral expiration status -> 0

RA Status: OK (0x0)
Quote is trusted.
MRTD matched.
MRSEAM matched.
MRSIGNERSEAM matched.
RTMR[0] matched.
RTMR[1] matched.
RTMR[2] matched.
RTMR[3] matched.
MRCONFIGID matched.
MROWNER matched.
MROWNERCONFIG matched.
TD is not in Debug mode.
Collateral hasn't expired.
672
536

[Supplemental Data]
version                          -> 3.4
earliest_issue_date              -> 2018-05-21T10:45:10+00:00
latest_issue_date                -> 2026-04-06T08:21:38+00:00
earliest_expiration_date         -> 2026-05-06T05:12:08+00:00
tcb_level_date_tag               -> 2024-11-13T00:00:00+00:00
pck_crl_num                      -> 1
root_ca_crl_num                  -> 1
tcb_eval_ref_num                 -> 18
root_key_id                      -> 46e403bd34f05a3f2817ab9badcaacc7ffc98e0f261008cd30dae936cace18d5dcf58eef31463613de1570d516200993
pck_ppid                         -> d9ade6cf7a7e4d2f4871b803ba765180
tcb_cpusvn                       -> 03030202040100050000000000000000
tcb_pce_isvsvn                   -> 13
pce_id                           -> 0
tee_type                         -> 0x0
sgx_type                         -> 1
platform_instance_id             -> 7a42b971218ed887c723b5f561607e39
dynamic_platform                 -> TRUE
cached_keys                      -> TRUE
smt_enabled                      -> TRUE
sa_list                          -> (empty)
qe_iden_earliest_issue_date      -> N/A
qe_iden_latest_issue_date        -> N/A
qe_iden_earliest_expiration_date -> N/A
qe_iden_tcb_level_date_tag       -> N/A
qe_iden_tcb_eval_ref_num         -> 0
qe_iden_status                   -> OK

SMT is enabled, allowed by user's policy.
Sufficient TCB Evaluation Dataset Number.
No Security Advisories reported.
Report Data matched.

Attester is Trusted. Accept RA.

Display TD Event Log? (y/N): n
Display IMA runtime measurements? (y/N): n
Secure Add Result: 100 + 200 = 300
[cleanup] Removed ./pinned_attester_cert.pem
```

As shown above, you are asked midway whether to display the TD event log (the measurement log up to the OS kernel) and the IMA log (the measurement log beyond the OS kernel); enter `y` to display them if needed.  
After RA, as shown above, a simple secure computation is performed (two integers are sent securely, the TD computes their sum, and the result is received securely and displayed).

## Applications of This Framework
Since this framework is a Python-based, highly readable implementation that adopts Attested-TLS, it is easier than past Humane-series frameworks to layer your own custom workloads on top of it.

By simply extending what the RP side does at `call_add_api()` in `rp_client.py` and what the Attester side does at the `@app.post("/add")` API in `api.py`, you can implement a variety of REST-API-based Attested TEE implementations.

## Known Issues
* As of 2026/4/17, the Linux kernel is implemented in such a way that IMA does not extend the measured value into RTMR[2]. As things stand, user workloads and the like cannot be measured, so you need to apply a patch that does make them measurable — for example, by combining it with something like [this](https://github.com/cc-api/container-integrity-measurement-agent). Once a stable countermeasure is established, we plan to roll it out in this repository as well.

* Beyond the OS kernel, IMA can perform measurements, but there is an IMA-specific issue in that the IMA policy itself is not measured and can therefore be modified. If this is also resolved, we plan to roll the fix out in this repository.

## About the License
The contents of this repository are developed by the same developer, partly reusing content from [Humane-RAFW-DCAP](https://github.com/iisec-suzaki/Humane-RAFW-DCAP) and [Humane-RAFW-MAA](https://github.com/acompany-develop/Humane-RAFW-MAA/). For the reused parts, we inherit the MIT license as per those repositories. For the content newly added in this repository, we likewise publish it under the MIT license.

---

本リポジトリは、Intel TDXのDCAPベースのRemote Attestation（RA）を、検証用付属情報（コラテラル）をPCCSというキャッシュサーバにキャッシュさせながらの完全な公式想定の形で、「人道的な」（Humane）難易度で手軽に実現する事のできるRAフレームワーク（RAFW）のコードやリソースを格納しています。  
ただし、本リポジトリはあくまでもベアメタルマシン上でTDX環境を構築し、その上でTDを動作させてそれに対するRAを実施するシナリオを想定しています。特に、AzureにおけるTDX VMインスタンスにおけるAttestationとは基本的に互換性が無い点に注意してください。

* [公式のTDX RAサンプル](https://github.com/intel/confidential-computing.tee.dcap/blob/DCAP_1.25/QuoteGeneration/quote_wrapper/tdx_attest/test_tdx_attest.c)は、それこそ同じRA基盤を持つIntel SGXと比較すると、劇的に改善されました。しかし、この検証側サンプルコードはこれとは別のプログラムとして提供されており、エンドツーエンドの形にはなっていません。本リポジトリでは、特に単一の関数を呼び出すだけでRAを完遂させる事のできる便利なインタフェースを提供しており、E2EでのRA実装の難易度が劇的に改善されます。

* Humane-AFWシリーズにおけるEPID-RA用フレームワークである先代の[Humane-RAFW](https://github.com/acompany-develop/Humane-RAFW)同様、複雑なAutomakeやシェルスクリプトによる難解な自動生成要素を排しており、開発者は新たに加えたい要素をMakefileやコード中に簡潔に加える事が出来ます。

* TDXホスト側設定、TD構築方法、TD内設定、PCCS構築方法等、バージョンや文献により非常に散逸している手順を一意に確立し、その方法を細かく掲載しています。よって、TDXで動かすものは存在するがそもそもTDXのベアメタルでの構築手順が不明、といった状況にも陥りにくいです。

* SGXと異なりCVMであるTDXでは動かせるワークロードの自由度が非常に高いため、本リポジトリの内容は基本的にPythonで実装しています。また、検証側コードはSGXと共通のQvLを用いますが、こちらもFFIによりPythonから操作できるようになっています。いずれにせよ、旧EPID-RAの公式サンプルにあったmsgioのような致命的なオーバーヘッドを抱えた通信用関数により頭を悩まされる事はありません。

* 本リポジトリでは、Relying Party（RP）とAttesterの暗号通信方式としてAttested-TLSを採用しています。具体的には、ホスト名検証なしの証明書ピンニングを採用し、RPとAttesterでTLSハンドシェイクしReport Dataでの中間者攻撃対策及び鮮度対策も行いながら暗号通信路を確立する事で、通信相手が真にRA済みのTEE内ワークロードである事を保証できるようになっています。このような実装は公式のDCAP-RAサンプルには存在しないため、暗号通信路実装の手間の大幅な削減を行う事ができます。

* RPは、TOMLファイル（reference.toml）の中身を設定する事で、期待する測定値（リファレンス測定値）の指定や、その他どのような条件であれば受理するかといった指定をきめ細やかに行う事ができます。これにより、受理すべきAttesterの条件を高粒度に設定する事ができます。

* Quote及び補足情報（Supplemental Data）の中身をラベル付きで表示する事で、検証対象TDの実態をより把握しやすくしています。また、TD Quoteはバージョン4（`sgx_quote_4.h`準拠）とバージョン5（`sgx_quote_5.h`）の双方に対応しています。

* Verifierとしての機能は、RP側が兼ねる設計にしています。これにより、第三者検証機関を信頼しなければならない必要性を無くし、より信頼可能範囲を小さくする事ができます。

* 検証にはQvLを使用し、QvEは使用しません。これは、QvEを採用するとVerifier（RP）もSGX対応マシンを用意しなければならないためです。かつ、TDからSGX EnclaveをLAする事は不可能であるため、相互RAにおいて信頼度の高いローカルVerifierとして利用する事もできません。このように、TDXにおいてはQvEを利用するメリットはほぼ存在しないため、意図的に採用しないようにしています。

* PyInstallerによりバイナリ化して実行する事で、IMAの実行時チェックで測定できるようにしています。これにより、ログが肥大化しがちなファイル読み取り時チェックを有効化しなくても、IMAにより測定する事が可能になります。

## 動作確認環境
### Attester
* ホストOS：Ubuntu 25.10
* ホストOSカーネル：6.17.0-20-generic
* TDX Moduleバージョン：1.5.13（MRSEAM値より特定）
* ゲストOS：Ubuntu 24.04.4 LTS
* ゲストOSカーネル：6.8.0-107-generic
* SGX DCAP：バージョン1.25

### Relying Party
* OS：Ubuntu 24.04.4 LTS
* OSカーネル：6.17.0-1010-azure
* SGX DCAP：バージョン1.25

## TDX環境構築
RAには直接は関係しませんが、TDXのベアメタルマシン上での構築は、その手順が非常に厄介であるという事実があります。そこで、本READMEでは、フルディスク暗号化等は有効化しない、最低限TDを立ち上げてRAできるようにするまでの環境構築手順についても説明します。不要である方は適宜次のステップの説明まで読み飛ばしてください。

### メモリ要件
盲点となりやすいですが、TDXはRAを実行する上でSGXに依存しています。そして、このSGXは全メモリチャネルに最低1枚のDIMM（メインメモリ）が差さっていないと有効化できないという仕様となっています。よって、使用しているマシンのマニュアルと、実際のそのマシンのメモリの配置を見て、全メモリチャネル（全メモリスロットを埋める必要はありません）にDIMMが差さっているかを確認してください。

### BIOS設定
BIOS設定に関しては、マザーボードベンダごとに多種多様であるため、どうしても一意に説明できない部分があります。
例えば、DELL PowerEdge R660というマシンでは、以下のような設定によりTDXを有効化できます。
* BIOS設定画面はF2で入る。
* System BIOSに入る。
* Processor Settingsから以下の変更を加える。
    * CPU Physical Address LimitをDisabledにする。
    * Sub NUMA Clusterを2-Way Clusteringにする。
    * TEEにおけるセキュリティの観点から、Logical ProcessorはDisabledにしておく事を推奨。
* System Securityから以下の変更を加える。
    * Memory EncryptionをMultiple Keysにする。
    * Intel TDXをEnabledにする。
    * TDX SEAMをEnabledにする。
    * Intel SGXをEnabledにする。
* Memory Settingsで以下を確認する。
    * Node InterleavingがDisabledになっている事を確認する。ややこしいが、ここがDisabledだとNUMAが有効化されている状態になっている。

Sub NUMAの設定等は、Dellの手順書上は指定されていませんが、Supermicroの手順書では記述されているので念の為記載しています。また、Supermicroではメモリ暗号化鍵の識別子として機能する、物理アドレス範囲上のHKIDを何ビットにするかの設定（TME-MT Key ID BitsやTME-MT/TDX Key Split）も存在します。

それぞれについては説明しきれないため、各ベンダのマニュアルを参照してください。例として、以下にIntel公式、Dell、Supermicroのドキュメントのリンクを載せておきます。
- Intel：https://cc-enabling.trustedservices.intel.com/intel-tdx-enabling-guide/04/hardware_setup/
- Dell：https://www.dell.com/support/kbdoc/en-us/000226452/enableinteltdxondell16g
- Supermicro（X13DEG-Rマザーボードの場合）：https://www.supermicro.com/manuals/motherboard/X13/MNL-2645.pdf

### ホストOS設定
この手順はAttester側のホストOS上で実施する。
- まず、以下のコマンドを打つと恐らく以下のようになるはずなので、これを修正する必要がある。
    ```sh
    acompany@phy:~$ sudo dmesg | grep -i tdx
    [sudo: authenticate] Password: 
    [    8.185161] virt/tdx: BIOS enabled: private KeyID range [32, 64)
    [    8.185165] virt/tdx: initialization failed: Hibernation support is enabled
    ```

* `/etc/default/grub`を開き、以下のように変更する。
    ```sh
    # 変更前
    GRUB_CMDLINE_LINUX=""

    # 変更後
    GRUB_CMDLINE_LINUX="nohibernate kvm_intel.tdx=1"
    ```

* 変更を適用し再起動する。
    ```sh
    sudo update-grub
    sudo reboot
    ```

* 再起動後、先程と同じコマンドを打ち以下のような表示となれば成功。
    ```sh
    acompany@phy:~$ sudo dmesg | grep -i tdx
    [    0.000000] Command line: BOOT_IMAGE=/vmlinuz-6.17.0-20-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro nohibernate kvm_intel.tdx=1 crashkernel=2G-4G:320M,4G-32G:512M,32G-64G:1024M,64G-128G:2048M,128G-:4096M
    [    4.653640] Kernel command line: BOOT_IMAGE=/vmlinuz-6.17.0-20-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro nohibernate kvm_intel.tdx=1 crashkernel=2G-4G:320M,4G-32G:512M,32G-64G:1024M,64G-128G:2048M,128G-:4096M
    [    8.676579] virt/tdx: BIOS enabled: private KeyID range [32, 64)
    [    8.676583] virt/tdx: Disable ACPI S3. Turn off TDX in the BIOS to use ACPI S3.
    [   38.215820] virt/tdx: 6303780 KB allocated for PAMT
    [   38.215825] virt/tdx: module initialized
    ```

* 以下のコマンドを実行し、QEMUとlibvirtをインストールする。
    ```sh
    sudo apt update
    sudo apt install qemu-system-x86 libvirt-daemon-system libvirt-clients
    ```

* 実行ユーザをkvmグループに追加する。
    ```sh
    sudo usermod -aG kvm $USER
    ```

* 再起動等でグループ追加を反映させたら、`/etc/libvirt/qemu.conf`をroot権限（sudo付き）で開き、以下の3行をファイル末尾に追加する。
    ```sh
    user = "<your_user_name>"
    group = "kvm"
    dynamic_ownership = 0
    ```
    `<your_user_name>`部分は実行中のユーザ名にする（例：`user = "acompany"`）。

* `libvirtd`を再起動し、続いてマシンも再起動する。
    ```sh
    sudo systemctl restart libvirtd
    sudo reboot
    ```
    再起動後、libvirtdがactiveである事を確認する。

### TDイメージの作成と起動
Attesterマシンのホスト上で実施。
* CanonicalのTDXリポジトリをCloneする。
    ```sh
    git clone https://github.com/canonical/tdx.git
    ```

* Ubuntu 24.04ベースでTDイメージを作成する。なお、2026/4/16現在、Ubuntu 25.04での作成も可能。ただし、TDX含む諸々のCVM機能がIn-kernel化されたUbuntu 25.10で作成できるのかは未検証。
    ```sh
    cd tdx/guest-tools/image/
    sudo ./create-td-image.sh -v 24.04
    ```
    TDイメージの作成に成功すると、最後の方に以下のようなメッセージが表示される。
    ```sh
    SUCCESS: Run setup scripts inside the guest image
    INFO: Cleanup!
    SUCCESS: TDX guest image : /home/acompany/Develop/tdx-ncc/tdx/guest-tools/image/tdx-guest-ubuntu-24.04-generic.qcow2
    ```

* Relying Party（RP）からの通信を受信するために、TDへの疎通設定を行う必要がある。疎通させるには色々あるが、今回はTDにローカルIPを割り当て、必要なポートへの外部からの通信をTDにルーティングする、ごく簡単な設定を行う。本番環境等、実運用時はブリッジを作成する等をした方が良い。まず、現在使われているネットワークインタフェースを特定する。
    ```sh
    ip route show
    ```
    すると以下のように表示されるため、1行目に出てくるネットワークインタフェース名を控える。以下の例では `ens51f0np0`が相当。
    ```sh
    default via 133.125.0.1 dev ens51f0np0 proto static 
    133.125.0.0/24 dev ens51f0np0 proto kernel scope link src 133.125.0.65 
    192.168.122.0/24 dev virbr0 proto kernel scope link src 192.168.122.1
    ```
    そのマシンのIPが割り当てられているインタフェースを特定できれば良いので、`ifconfig`等他の方法でも勿論問題ない。特定したインタフェース名は後で使用するので控えておく事。

* 先程CloneしたCanonicalのTDXリポジトリフォルダ（`tdx`）内の、`guest-tools/trust_domain.xml.template`を開き、以下の部分を削除する。
    ```xml
    <qemu:commandline>
        <qemu:arg value='-device'/>
        <qemu:arg value='virtio-net-pci,netdev=nic0,bus=pcie.0,addr=0x5'/>
        <qemu:arg value='-netdev'/>
        <qemu:arg value='user,id=nic0,hostfwd=tcp::0-:22'/>
    </qemu:commandline>
    ```
    このxml.templateファイルは、念の為事前にバックアップを取っておいても良い。

* 同じく`guest-tools`フォルダ内で、以下のコマンドを実行しTDの作成を実施する。
    ```sh
    ./tdvirsh new --td-image ./image/tdx-guest-ubuntu-24.04-generic.qcow2
    ```

* 数分すると実行が完了するので、以下のコマンドで正常に作成できたかを確かめておく。この時、以下のようにIPアドレスも表示されるため、このIPアドレスは控えておく事。
    ```sh
    acompany@phy:~/Develop/tdx-ncc/tdx/guest-tools$ ./tdvirsh list
    Id   Name                                                        State 
    ---------------------------------------------------------------------------- 
    8    tdvirsh-trust_domain-84fcc6bb-ca37-400c-9a39-57ec5a92c0b3   running (ip:192.168.122.30, hostfwd:, cid:3)
    ```

* 余談であるが、TDにはコンソールでログインする事もできる。ユーザ名は`tdx`, パスワードは`123456`。
    ```sh
    ./tdvirsh console tdvirsh-trust_domain-e98650e2-8ab1-4663-9831-1913e224af64
    login: tdx
    password: 123456
    ```
    その後、MacであればCommand+]でコンソールを抜ける事ができる。

* ホスト側で、以下のiptables設定を行う。以下はTD内のIPアドレスが192.168.122.30である例。
    ```sh
    sudo iptables -t nat -A PREROUTING -p tcp --dport 8443 -j DNAT --to-destination 192.168.122.30:8443

    sudo iptables -I FORWARD 1 -i ens51f0np0 -o virbr0 -p tcp --dport 8443 -d 192.168.122.30 -j ACCEPT
    sudo iptables -I FORWARD 2 -i virbr0 -o ens51f0np0 -m state --state RELATED,ESTABLISHED -j ACCEPT

    sudo iptables -t nat -A PREROUTING -p tcp --dport 2222 -j DNAT --to-destination 192.168.122.30:22
    sudo iptables -I FORWARD 3 -i ens51f0np0 -o virbr0 -p tcp --dport 22 -d 192.168.122.30 -j ACCEPT
    ```
    実際には違うIPとネットワークインタフェースになるはずなので、`192.168.122.30`の部分と`ens51f0np0`の部分は自身の環境の実際の値に置き換えて実行する事。  
    TDを再起動した場合、IPが変わる可能性があるため、以下のコマンドを実行後に上記のiptables手順を再実行する。
    ```sh
    sudo iptables -t nat -F PREROUTING
    sudo iptables -D FORWARD 1
    sudo iptables -D FORWARD 1
    ```

* TDにSSHでログインする。
    ```sh
    ssh -p 22 root@<上記IP> #特権ユーザ
    ssh -p 22 tdx@<上記IP> #非特権ユーザ
    ```

* ログインしたついでに、TD内の基本的な設定だけ済ませてしまう。まず、QGS（TD Quote作成サービス）との通信方法を設定するため、TD内で以下のコマンドを実行する。
    ```sh
    sudo tee -a /etc/tdx-attest.conf > /dev/null <<EOT
    port=4050
    EOT
    ```

* 次に、TD内で以下のコマンドを実行し、TDX/SGX用IntelリポジトリのGPGキーの追加を実施する。
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* TD内で`/etc/apt/sources.list.d/ubuntu.sources`をroot権限で開き、末尾に以下を追記する。
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```
    その後、apt updateを実施する。
    ```sh
    sudo apt update
    ```

* TD内でTDX RA用ライブラリをインストールする。
    ```sh
    sudo apt install -y libtdx-attest libtdx-attest-dev
    ```

### TD内IMA設定
ユーザワークロード等、OSカーネルよりも先のコンテンツを測定するには、LinuxのIMA機能を用いる必要がある。よって、このIMAに関する設定も実施する。
* TDにログインし、`/etc/`フォルダ配下に`ima`というフォルダを作成する。
    ```sh
    sudo mkdir /etc/ima
    ```

* 作成したフォルダに移動し、`ima-policy`というファイルを作成する。**これ以降、不完全な状態でTDの電源が落ちると復元不能な破壊を招くおそれがあるため、続く手順以外の方法では絶対にTDを落とさない事。**
    ```sh
    cd /etc/ima
    sudo touch ima-policy
    ```

* 作成した上記ファイルに以下の内容を記載する。FILE_CHECKの行は、必要性がなければコメントアウトのままで良い。
    ```
    # PROC_SUPER_MAGIC
    dont_measure fsmagic=0x9fa0
    # SYSFS_MAGIC
    dont_measure fsmagic=0x62656572
    # DEBUGFS_MAGIC
    dont_measure fsmagic=0x64626720
    # TMPFS_MAGIC
    dont_measure fsmagic=0x1021994
    # DEVPTS_SUPER_MAGIC
    dont_measure fsmagic=0x1cd1
    # BINFMTFS_MAGIC
    dont_measure fsmagic=0x42494e4d
    # SECURITYFS_MAGIC
    dont_measure fsmagic=0x73636673
    # SELINUX_MAGIC
    dont_measure fsmagic=0xf97cff8c
    # SMACK_MAGIC
    dont_measure fsmagic=0x43415d53
    # CGROUP_SUPER_MAGIC
    dont_measure fsmagic=0x27e0eb
    # CGROUP2_SUPER_MAGIC
    dont_measure fsmagic=0x63677270
    # NSFS_MAGIC
    dont_measure fsmagic=0x6e736673 

    # 測定対象及び測定トリガの設定

    # プログラムの実行に際してMMAPされるファイルの測定
    measure func=MMAP_CHECK mask=MAY_EXEC

    # 実行されたバイナリプログラムの測定
    measure func=BPRM_CHECK mask=MAY_EXEC

    # root (uid=0) によってopenされたファイルの測定
    # measure func=FILE_CHECK mask=MAY_READ uid=0

    # ロードされたカーネルモジュールの測定
    measure func=MODULE_CHECK

    # カーネルにロードされたファームウェアの測定
    measure func=FIRMWARE_CHECK
    ```

* TDからログアウトし、ホストOSに戻る。

* 前述のCanonicalのtdxリポジトリフォルダ内のtdvirshが入っているフォルダ`guest-tools`に移動しておく。必要に応じて、`./tdvirsh list --all`で当該TDのNameを確認しておく。

* 当該TDを以下のコマンドでシャットダウンする。
    ```sh
    ./tdvirsh shutdown <tdname>
    ```
    一例は以下の通り。
    ```sh
    ./tdvirsh shutdown tdvirsh-trust_domain-745eb08d-790c-4685-81c4-92ae69119a68
    ```

* TDをシャットダウンできた事を確認する。
    ```sh
    ./tdvirsh list --all
    Id   Name                                                        State 
    ---------------------------------------------------------------------------- 
    -    tdvirsh-trust_domain-745eb08d-790c-4685-81c4-92ae69119a68   shut off (ip:unknown, hostfwd:, cid:)
    ```

* シャットダウンしたTDを起動する。これにより再起動した事になり、追加したIMAポリシが反映される。
    ```sh
    ./tdvirsh start <tdname>
    ```

### TDX RAインフラの構築
より簡単に構築するのであればTDXマシンのローカル完結にしてしまうのが良いが、拡張性も考えてVerifier及びRPを別マシンに配置する設計での構築手順を説明する。

手元では、Azureで適当なインスタンス（例：Standard D4s v5）を立てて使用しているが、その限りでなくとも良い。OSはUbuntu 24.04にしている。以下、このマシンを「RPマシン」と呼ぶ。

#### PCCSの構築
RPマシンで実施。
* 以下のコマンドを実行してIntelのGPGキーを追加する。
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* `/etc/apt/sources.list.d/ubuntu.sources`を開き、最下部に以下を追加する。
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* 上記追加を反映させる。
    ```sh
    sudo apt update
    ```

* PCCSに必要な前提パッケージをインストールする。
    ```sh
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -yq --no-install-recommends nodejs=20.11.1-1nodesource1
    sudo apt-get install -y cracklib-runtime
    ```

* PCCSをインストールする。
    ```sh
    sudo apt install -y --no-install-recommends sgx-dcap-pccs
    ```
    すると、以下のように対話式で入力を求められるので、下記の通り入力する。特に、Caching Fill Methodは必ずLAZYにする事。
    ```
    Do you want to install PCCS now? (Y/N) :y
    Enter your http proxy server address, e.g. http://proxy-server:port (Press ENTER if there is no proxy server) :
    Enter your https proxy server address, e.g. http://proxy-server:port (Press ENTER if there is no proxy server) :

    Do you want to configure PCCS now? (Y/N) :y
    Set HTTPS listening port [8081] (1024-65535) :
    Set the PCCS service to accept local connections only? [Y] (Y/N) :n
    Set your Intel PCS API key (Press ENTER to skip) :<PCS_PRIMARY_KEY>
    Choose caching fill method : [LAZY] (LAZY/OFFLINE/REQ) :LAZY

    Set PCCS server administrator password:<任意のPCCS管理者パスワードを入力>
    Re-enter administrator password:<任意のPCCS管理者パスワードを再入力>
    Set PCCS server user password:<任意のPCCSユーザパスワードを入力>
    Re-enter user password:<任意のPCCSユーザパスワードを再入力>

    Do you want to generate insecure HTTPS key and cert for PCCS service? [Y] (Y/N) :y
    Certificate request self-signature ok
    subject=CN = PCCS Server (self-signed certificate)
    Installing PCCS service ...Created symlink /etc/systemd/system/multi-user.target.wants/pccs.service → /usr/lib/systemd/system/pccs.service.
    finished.
    Installation completed successfully.
    ```
    PCSのAPIキーは、以下のリンク先で取得する。（リンク先のSubscribeボタンから進む）  
    https://api.portal.trustedservices.intel.com/provisioning-certification  
    また、PCCSの管理者・ユーザパスワードは忘れないように控えておく事。

#### PCCSコラテラルの準備（Attester）
一旦TDXマシン（Attesterマシン）に戻り、RAに必要な付属情報であるコラテラルの準備を行う。TDXマシンがマルチCPUマシンである前提であるが、シングルCPUであっても同様の手順で進められるはずである（要検証）。
* TDXマシンのホスト側にて、以下のコマンドを実行しIntelのGPGキーを追加する。
    ```sh
    wget https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key
    sudo mkdir -p /etc/apt/keyrings
    sudo cp intel-sgx-deb.key /etc/apt/keyrings/intel-sgx-keyring.asc
    sudo chmod 644 /etc/apt/keyrings/intel-sgx-keyring.asc
    ```

* `/etc/apt/sources.list.d/ubuntu.sources`を開き、最下部に以下を追加する。
    ```
    Types: deb
    URIs: https://download.01.org/intel-sgx/sgx_repo/ubuntu
    Suites: noble
    Components: main
    Architectures: amd64
    Signed-By: /etc/apt/keyrings/intel-sgx-keyring.asc
    ```
    Intelが25.10用リポジトリをまだ用意していないため、代わりに24.04（noble）のものを代用する。

* 上記追加を反映させる。
    ```sh
    sudo apt update
    ```

* PCKCIDRT（PCK Cert ID Retrieval Tool）をインストールする。
    ```sh
    sudo apt install -y sgx-pck-id-retrieval-tool
    ```

* PCKCIDRTを実行し、Platform Manifest等を含んだCSVの取得を実施する。
    ```sh
    cd /opt/intel/sgx-pck-id-retrieval-tool
    sudo ./PCKIDRetrievalTool -f host_$(hostnamectl --static).csv
    ```
    **このCSVは、一度取得するとSGX Factory Resetをかけるまで二度と取り出せなくなるので紛失に注意。**

* 上記CSVからPlatform Manifestをバイナリ形式で抽出する。
    ```sh
    sudo apt-get install -y csvtool
    sudo bash -c "csvtool col 6 host_$(hostnamectl --static).csv | xxd -r -p > host_$(hostnamectl --static)_pm.bin"
    ```

* Platform ManifestのバイナリをIRS（Intel Registration Service）に送信する。
    ```sh
    curl -i \
        --data-binary @host_$(hostnamectl --static)_pm.bin \
        -X POST "https://api.trustedservices.intel.com/sgx/registration/v1/platform" \
        -H "Content-Type: application/octet-stream"
    ```
    成功すると以下のように成功のHTTPステータスが返ってくるはずである。
    ```
    HTTP/1.1 201 Created
    Content-Length: 32
    Content-Type: text/plain
    Request-ID: adcc371c43d84b12bbd6fd334651fdfc
    Date: Mon, 06 Apr 2026 05:53:15 GMT
    ```

* 一旦作業フォルダに戻り、DCAPライブラリをCloneする。
    ```sh
    git clone --recursive https://github.com/intel/confidential-computing.tee.dcap.git
    ```

* 必要パッケージのインストールを行う。
    ```sh
    sudo apt install -y python3 python3-pip python3-venv
    ```

* PCS Client Toolのフォルダに移動し、venvを有効化する。その後、必要なPythonパッケージをインストールする。
    ```sh
    cd confidential-computing.tee.dcap/tools/PcsClientTool/
    python3 -m venv venv
    source ./venv/bin/activate
    pip install -r requirements.txt
    ```

* PCKCIDRTで先程取得したCSVを、PCS Client Toolのフォルダにコピーする。
    ```sh
    cp /opt/intel/sgx-pck-id-retrieval-tool/host_$(hostnamectl --static).csv .
    ```

* 以下のコマンドを実行し、プラットフォーム情報の収集を実施する。
    ```sh
    python3 ./pcsclient.py collect -d .
    ```

* 以下のコマンドを実行し、コラテラルの収集を実施する。その後、一旦venv環境を抜ける。
    ```sh
    ./pcsclient.py fetch -t early -o platform_collaterals.json
    deactivate
    ```
    もしGCP等で本リポジトリの手順を踏襲している場合は、収集コマンドとして代わりに以下を実行した方が良い。あるいはベアメタルでも以下のコマンドを実行するのでも特に支障は出ないと思われる。
    ```sh
    ./pcsclient.py fetch -p all -t early -o platform_collaterals.json
    ```
    いずれにせよ、途中、PCSのAPIキーの入力を求められるので、前述の手順で控えておいたものを入力する。直後、Keyringへの登録をするか聞かれるが、却下（nと入力）しておく。  
    また、以下のような表示が出る事があるが、以下のように入力し無視して良い。
    ```
    Some certificates are 'Not available'. Do you want to save the list?(y/n)y
    Please input file name (Press enter to use default name not_available.json):
    Please check not_available.json for 'Not available' certificates.
    ```

#### PCCSコラテラルの準備（RP）
このセクションの手順はRPマシンで実施する。
* PCCS Admin Toolが入っているリポジトリをCloneする。
    ```sh
    git clone --recursive https://github.com/intel/confidential-computing.tee.dcap.pccs.git
    ```

* クローンしたフォルダ内のPccsAdminToolフォルダに移動し、venv環境を作る。
    ```sh
    cd confidential-computing.tee.dcap.pccs/PccsAdminTool
    sudo apt install python3-venv
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

* 先程Attesterマシンで取得したplatform_collaterals.jsonを、scpコマンドやUSBによる移動等でRPマシンに持ってきておく。

* 収集したコラテラルをRPマシン上のPCCSに登録する。
    ```sh
    ./pccsadmin.py put -i platform_collaterals.json
    deactivate
    ```

* RPマシン上のPCCSには、RA時にポート8081経由でアクセスが発生する。よって、Azure VM等でRPマシンを立てている場合は、VM管理ページからポート8081への疎通を許可する受信ポートルールを設定する。ベアメタルマシンでRPを動かしている場合にも、ファイアウォール等が阻害していないかを確認する事。

#### TD Quote生成環境の構築
Attester（TDX）マシンにて実施する。
* ホスト側にて以下のコマンドを実行し、QGS（Quote Generation Service）及びそれに必要なパッケージのインストールする。
    ```sh
    sudo apt install -y \
    tdx-qgs \
    libsgx-dcap-default-qpl \
    libsgx-dcap-ql
    ```

* QGSのサービスログを確認したい場合は、任意で以下のコマンドを実行する。
    ```sh
    sudo journalctl -u qgsd -f
    ```
    以下のように出ていれば正常。
    ```
    Apr 06 06:15:35 phy usermod[94009]: add 'qgsd' to group 'sgx_prv'
    Apr 06 06:15:35 phy usermod[94009]: add 'qgsd' to shadow group 'sgx_prv'
    Apr 06 06:15:35 phy usermod[94016]: add 'qgsd' to group 'sgx'
    Apr 06 06:15:35 phy usermod[94016]: add 'qgsd' to shadow group 'sgx'
    Apr 06 06:15:35 phy qgs[94024]: Parameters from configuration file: num_thread = 4, port = 4050 (0fd2h)
    Apr 06 06:15:35 phy qgs[94024]: Parameters after command line check: num_thread = 4, port = 4050 (0fd2h)
    Apr 06 06:15:35 phy systemd[1]: Started qgsd.service - Intel(R) TD Quoting Generation Service.
    Apr 06 06:15:35 phy qgsd[94027]: Added signal handler
    Apr 06 06:15:35 phy qgsd[94027]: About to create QgsServer
    Apr 06 06:15:35 phy qgsd[94027]: About to start main loop
    ```

* コラテラル取得の宛先等を指定する、 /etc/sgx_default_qcnl.conf の設定を行う。
    ```sh
    sudo vim /etc/sgx_default_qcnl.conf
    ```
    以下の部分がデフォルトでは`true`になっているので`false`にする。
    ```json
    ,"use_secure_cert": false
    ```
    PCCSの証明書として自己署名証明書ではないまともなものを使えばここは逆にtrueにすべきではあるが、TEE RAとは直接関係しないサーバ証明書の話になるので、ここでは自己署名証明書で簡略化する。  
    また、`"pccs_url"`の`localhost`部分は、実際のRP/VerifierマシンのIPアドレスに変更しておく。

* 上記の変更を反映させるため、サービスを再起動させる。
    ```sh
    sudo systemctl restart qgsd.service
    ```

### TDX Attestationのサンプル実行
* TDにログインし、以下のコマンドを実行する。
    ```sh
    cd /opt/intel/tdx-quote-generation-sample/
    sudo make
    sudo ./test_tdx_attest
    ```
    成功するとTD Quoteの作成まで成功する。RTMR2/3にExtendできないのは、Ubuntu 24.04がデフォルトで使用しているLinuxカーネルのバージョン時点で抱えている不具合である。カーネルをアップグレードし、6.16以降にすればExtendできるようになるが、ここではその手順は割愛する。

## RAフレームワークの準備と実行
実際に本リポジトリの提供するフレームワークを用いてTDX RAを行うための手順を説明します。

### Attester側準備
* TD内にて本リポジトリをCloneする。
    ```sh
    git clone https://github.com/acompany-develop/Humane-RAFW-TDX.git
    ```

* リポジトリのフォルダ内の`attester`フォルダに入る。
    ```sh
    cd attester
    ```

* 以下のコマンドを実行し、venv環境を整える。
    ```sh
    sudo apt install python3-venv
    python3 -m venv venv 
    source venv/bin/activate
    ```

* 必要なPythonパッケージをインストールする。
    ```sh
    pip3 install -r requirements.txt
    ```

### RP側準備
* 以下のコマンドを実行し、必要なパッケージのインストールを実施する。
    ```sh
    sudo apt install -y libsgx-dcap-quote-verify-dev libsgx-dcap-default-qpl libsgx-dcap-default-qpl-dev libsgx-enclave-common-dev libtdx-attest libtdx-attest-dev
    ```

* コラテラル取得の宛先等を指定する、 /etc/sgx_default_qcnl.conf の設定を行う。Quote検証時にもコラテラルを使うため、RP側でも設定が必要。
    ```sh
    sudo vim /etc/sgx_default_qcnl.conf
    ```
    以下の部分がデフォルトでは`true`になっているので`false`にする。

* 反映のためにPCCSサービスを再起動する。
    ```sh
    sudo systemctl restart pccs.service
    ```

* 本リポジトリをCloneする。
    ```sh
    git clone https://github.com/acompany-develop/Humane-RAFW-TDX.git
    ```

* 以下のコマンドを実行し、venv環境を整える。
    ```sh
    sudo apt install python3-venv
    python3 -m venv venv 
    source venv/bin/activate
    ```

* 必要なPythonパッケージをインストールする。
    ```sh
    pip3 install -r requirements.txt
    ```

### リファレンス測定値の取得
この手順は、運用上はRPの人間がAttesterマシンにログインして実施するものです。RPがAttesterマシンをリモートにデプロイする前に、予めリファレンス測定値を取得しておくシナリオを想定しています。
* AttesterマシンのTD内において、上述までの設定を全て完了させておく。

* 手順を完了させてあれば`attester`側のvenvに入った状態であるはずである。その状態のまま、AttesterマシンのTD内における、本リポジトリのフォルダ内のrelying-party/reference-toolフォルダ内に移動する。

* 以下のコマンドを実行し、リファレンス測定値取得ツールを実行する。
    ```sh
    sudo make all
    ```
    sudoをつけないとQuoteの取得ができず、実行に失敗するので注意。  
    実行に成功すると以下のような表示が出る。
    ```
    [*] Generating TD Quote...
    [*] Quote size: 5243 bytes
    [*] Quote version : 4
    [*] TEE type      : 0x00000081

    === Reference Measurements ===
    MRSEAM         : 27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec

    MRSIGNERSEAM   : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MRTD           : eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542

    MRCONFIGID     : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MROWNER        : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    MROWNERCONFIG  : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

    RTMR[0]        : 2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d

    RTMR[1]        : f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877

    RTMR[2]        : 4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b

    RTMR[3]        : 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
    ```
    この内容はコピーする等して控えておく。

* RPマシンに戻り、`relying-party`フォルダ内の`reference_template.toml`を`reference.toml`としてコピーする。
    ```sh
    cp reference_template.toml reference.toml
    ```

* reference.tomlを開く。`mr_seam`, `mrsigner_seam`, `mr_td`, `mrconfigid`, `mrowner`, `mrownerconfig`, `rtmr0〜rtmr3`の右辺は、先程のリファレンス測定値取得ツールで表示された16進数文字列を、二重引用符で囲んでペーストする。  
    一例：
    ```toml
    [measurements]
    mr_seam = "27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec"
    mrsigner_seam = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_td = "eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542"

    mr_config_id = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_owner = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    mr_owner_config = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

    rtmr0 = "2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d"
    rtmr1 = "f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877"
    rtmr2 = "4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b"
    rtmr3 = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    ```

* tomlの残りのフィールドは、必要無ければデフォルト値で良い。必要があれば以下を参考に適宜変更する。
    | フィールド名 | 説明 | 推奨値 |
    |---|---|---|
    | `allow_debug` | TDのデバッグモードを許可するか。デバッグモードが有効化されていると、専用インタフェースを通じて外部からTD内のメモリ内容を平文で読み書きできてしまうため、本番環境では使用してはならない。 | `false` |
    | `allow_collateral_expiration` | RAに使用する付属情報（コラテラル）の期限切れを許可するか。期限切れを起こしていても直ちに危険ではないため、一旦は許容でも問題ない。参考までに、Azureでは管理が滞っているため、問答無用で期限切れの状態でRAをする必要がある。 | `true` |
    | `allow_configuration_needed` | RAステータスの1つである、`CONFIGURATION_NEEDED`を許容するか。これは、TEEは最新化されているが、安全性を高める上で何らかのマシン設定変更が必要である事を意味する。SGXにおける過去のEPID-RAでは例えばハイパースレッドを有効化しているとこのステータスになっていたが、現行のSGX/TDX DCAP-RAでは有効化していても出ないため、何が影響するのかは不明。どうしてもこのステータスを消せないようであれば、一定のリスクを承知の上で許容できる。 | `false` |
    | `allow_sw_hardening_needed` | RAステータスの1つである、`SW_HARDENING_NEEDED`を許容するか。これは、マシンやTDXコンポネントは最新化されているが、脆弱性を無効化するにはTD内のコンテンツ（ユーザワークロード等）でも自前でソフトウェアレベルの対策を必要とする事を意味する。TCB Recovery（AttesterマシンのBIOSアップデート等）でもこのステータスが解決できない場合は、一定のリスクを承知の上で許容できる。 | `false` |
    | `allow_out_of_date` | RAステータスの1つである、`OUT_OF_DATE`を許容するか。これは、マシンや導入されたTDXが古くなっており、一定の安全性を維持できない事を意味する。TCB Recoveryで解決できる場合もあるが、そのマシン（CPU）でのアップデートがIntelにより打ち切られていたり、Intelによりアップデートが配布されていても、マザーボードベンダがそれをインストール可能な形にしていない可能性もあったりするため、これが出るとなかなか対策は難しい。基本的には拒否を強く推奨。 | `false` |
    | `allow_td_relaunch_advised` | RAステータスの1つである、`TD_RELAUNCH_ADVISED`を許容するか。これは、マシン側のTDX関連コンポネントは最新化されているが、対象のTDが最新化前に起動されているため、TDを再起動する事が推奨されている、というものである。実例を確認できていないが、再起動すれば直ると思われる。このRAステータスも拒否するに越した事は無い。 | `false` |
    | `allow_smt_enabled` | ハイパースレッドの有効化を許可するか。ハイパースレッドは潜在的にTEEに対する攻撃を助長するリスクがあるため（例：ZombieLoad攻撃、Gather Data Sampling攻撃）、無効化しておく事が望ましい。 | `false` |
    | `required_tcb_eval_ds_num` | そのTDX環境のセキュリティバージョンを端的に表現する、TCB Evaluation Dataset Numberという値について、その許容する下限値を指定する。必要がなければ0で良い。 | [こちら](https://www.intel.com/content/www/us/en/developer/topic-technology/software-security-guidance/trusted-computing-base-recovery-attestation.html)のページの表にある、`TCB-R Counter:`の右の数字と、表の内容から判断して設定する。不要であれば0 |
    | `allowed_sa_list` | 許容する脆弱性のリスト。Intel関連の脆弱性には、Intelによりセキュリティアドバイザリ（SA）が公開されており、さらにSAそれぞれにIDが振られている。例えばSGXにおけるMMIO Stale Data脆弱性には`INTEL-SA-00615`というIDが付与されている。このフィールドでは、危険性を考慮の上で許容すると判断した脆弱性を、このSAのIDで指定する。許容しない場合には空にする。 | 空 |

### Attester側の実行
* `attester`側のvenvに入った状態で、TD内の本リポジトリの`attester`フォルダで以下のコマンドを実行する。
    ```sh
    sudo make all
    ```
    sudoを付与しないとQuoteが取得できず、エラーとなるため注意。

### RP側の実行
* `relying-party`側のvenvに入った状態で、RPマシン上の本リポジトリの`relying-party`フォルダで、以下のコマンドを実行する。
    ```sh
    make all
    ```

### 実行例
#### Attester
```
INFO:     Started server process [13607]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8443 (Press CTRL+C to quit)
INFO:     20.243.195.59:60112 - "POST /attest HTTP/1.1" 200 OK
INFO:     20.243.195.59:60118 - "POST /add HTTP/1.1" 200 OK
```

#### RP
```
(venv) user@machine:~/Develop/tdx/Humane-RAFW-TDX/relying-party$ sudo make
./venv/bin/python3 rp_client.py
[config] ATTESTER_URL = https://133.125.0.65:8443/
/home/aos/Develop/tdx/Humane-RAFW-TDX/relying-party/venv/lib/python3.12/site-packages/urllib3/connectionpool.py:1097: InsecureRequestWarning: Unverified HTTPS request is being made to host '133.125.0.65'. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
  warnings.warn(
Obtained TD Quote successfully.
Quote size: 5243 bytes
Nonce sent: 86c33b6891453d35e012ee74e6237a31d5ff77e2b041026b5da58e01e502cc30
Saved pinned certificate: ./pinned_attester_cert.pem
Saved TD Event Log: ./tdeventlog.txt
Saved IMA runtime measurements: ./ima_runtime_measurements.txt

Quote version -> 4

TEE type -> 0x81


[Report Body in TD Quote]
MRSEAM               -> 27b67e0b20508f0acfb8a99df4283a7c86ae569d85d556a91d4eb20e56b5d42d5e65b31a3a6996e8e461f104f32fdeec

MRSIGNERSEAM         -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

SEAM Attributes      -> 0000000000000000

TD Attributes        -> 0000001000000000

XFAM                 -> e702060000000000

MRTD                 -> eea8b6a814569a52bd1e12f6b869bb2d9c0c8a7a43e658ffc3b42c199f116157ea7f04d359c7fdfd8ac483152cc13542

MRCONFIGID           -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

MROWNER              -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

MROWNERCONFIG        -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

RTMR[0]              -> 2a66fda697dc57788b7d1bf5f49a789f5a19f9516418818a87ed362d943ca433f5fe4f147c4e18a7cc9817a67f4dde5d

RTMR[1]              -> f858ed2aecba4ecd29084352c6b5c6e403c0bec89b8c852f90fa5a8cee796ffa095518c5cd8b92c25c1856e932a95877

RTMR[2]              -> 4551943829431064a863db04de6345622a614850ca2f6aced8b10df67ada1b6d433ba27015eda194a3fd09a81190a02b

RTMR[3]              -> 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

Report Data          -> 3d78d26597dadc7f0190f2a878129aedbb24b3e5a8c370c5a9f291c1faf3440dfc99e98510bd89382a1d5856fe47bcfd0f3d102ec48f92f474cf01757e0d05e4

Is TD in Debug mode? -> False

Collateral expiration status -> 0

RA Status: OK (0x0)
Quote is trusted.
MRTD matched.
MRSEAM matched.
MRSIGNERSEAM matched.
RTMR[0] matched.
RTMR[1] matched.
RTMR[2] matched.
RTMR[3] matched.
MRCONFIGID matched.
MROWNER matched.
MROWNERCONFIG matched.
TD is not in Debug mode.
Collateral hasn't expired.
672
536

[Supplemental Data]
version                          -> 3.4
earliest_issue_date              -> 2018-05-21T10:45:10+00:00
latest_issue_date                -> 2026-04-06T08:21:38+00:00
earliest_expiration_date         -> 2026-05-06T05:12:08+00:00
tcb_level_date_tag               -> 2024-11-13T00:00:00+00:00
pck_crl_num                      -> 1
root_ca_crl_num                  -> 1
tcb_eval_ref_num                 -> 18
root_key_id                      -> 46e403bd34f05a3f2817ab9badcaacc7ffc98e0f261008cd30dae936cace18d5dcf58eef31463613de1570d516200993
pck_ppid                         -> d9ade6cf7a7e4d2f4871b803ba765180
tcb_cpusvn                       -> 03030202040100050000000000000000
tcb_pce_isvsvn                   -> 13
pce_id                           -> 0
tee_type                         -> 0x0
sgx_type                         -> 1
platform_instance_id             -> 7a42b971218ed887c723b5f561607e39
dynamic_platform                 -> TRUE
cached_keys                      -> TRUE
smt_enabled                      -> TRUE
sa_list                          -> (empty)
qe_iden_earliest_issue_date      -> N/A
qe_iden_latest_issue_date        -> N/A
qe_iden_earliest_expiration_date -> N/A
qe_iden_tcb_level_date_tag       -> N/A
qe_iden_tcb_eval_ref_num         -> 0
qe_iden_status                   -> OK

SMT is enabled, allowed by user's policy.
Sufficient TCB Evaluation Dataset Number.
No Security Advisories reported.
Report Data matched.

Attester is Trusted. Accept RA.

Display TD Event Log? (y/N): n
Display IMA runtime measurements? (y/N): n
Secure Add Result: 100 + 200 = 300
[cleanup] Removed ./pinned_attester_cert.pem
```

途中、上記のようにTDイベントログ（OSカーネルまでの測定ログ）とIMAログ（OSカーネルより先の測定ログ）を表示するかを聞かれるため、必要な場合は`y`と入力して表示させてください。  
RA後は、上記のように簡単な秘密計算（整数を2つ安全に送り、その和をTDに計算させ、結果を安全に受け取り表示させる）が実行されます。

## 本フレームワークの応用
本フレームワークは、Attested-TLSを採用したPythonベースの可読性も高い実装となっているため、このフレームワークの上にさらに独自のワークロードを載せるといった事が今までのHumaneシリーズよりもしやすくなっています。

RP側が`rp_client.py`で`call_add_api()`にて、Attester側が`api.py`の`@app.post("/add")`APIにて行っているものを拡張するだけで、多様なREST APIベースのAttestedなTEE実装を行う事が可能です。

## 既知の問題点
* 2026/4/17現在、LinuxカーネルはIMAが測定した際にその値をRTMR[2]にExtendしないという実装になっています。このままではユーザワークロード等を測定できないため、例えば[こちら](https://github.com/cc-api/container-integrity-measurement-agent)等を組み合わせ、測定させるようなパッチを適用する必要があります。安定した対応策が確立されたら本リポジトリにも展開予定です。

* OSカーネルより先はIMAによって測定できますが、IMAポリシ自体は測定されないため変更できてしまうというIMA特有の問題があります。こちらも解決できた場合には本リポジトリに展開する予定です。

## ライセンスについて
本リポジトリの内容は、[Humane-RAFW-DCAP](https://github.com/iisec-suzaki/Humane-RAFW-DCAP)や[Humane-RAFW-MAA](https://github.com/acompany-develop/Humane-RAFW-MAA/)の内容を、同一の開発者が一部流用しつつ開発しています。流用部分については、それらのリポジトリに従いMITライセンスを継承します。また、本リポジトリで新規追加した内容についても、同様にMITライセンスで公開します。